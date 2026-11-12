// Package store saves scans to a SQLite database.
package store

import (
	"database/sql"
	"fmt"
	"runtime"
	"time"

	"github.com/malewis5/big-apple-connect/internal/collector"

	_ "modernc.org/sqlite"
)

// Times are stored as UTC with millisecond precision.
const timeFormat = "2006-01-02T15:04:05.000Z"

const schema = `
PRAGMA foreign_keys = ON;

-- One run of the collector.
CREATE TABLE IF NOT EXISTS scans (
	id              INTEGER PRIMARY KEY,
	kind            TEXT NOT NULL,
	started_at      TEXT NOT NULL,
	finished_at     TEXT NOT NULL,
	tool_version    TEXT NOT NULL,
	os              TEXT NOT NULL,
	arch            TEXT NOT NULL,
	connection_type TEXT NOT NULL CHECK (connection_type IN ('Ethernet', 'WiFi', 'Unknown'))
) STRICT;

-- One thing the collector did.
CREATE TABLE IF NOT EXISTS probes (
	id                       INTEGER PRIMARY KEY,
	scan_id                  INTEGER NOT NULL REFERENCES scans (id),
	method                   TEXT NOT NULL,
	target                   TEXT NOT NULL,
	concurrent_with_probe_id INTEGER REFERENCES probes (id),
	output                   TEXT,
	error                    TEXT,
	started_at               TEXT NOT NULL,
	finished_at              TEXT NOT NULL
) STRICT;

-- One fact read from a probe's response.
CREATE TABLE IF NOT EXISTS observations (
	id        INTEGER PRIMARY KEY,
	probe_id  INTEGER NOT NULL REFERENCES probes (id),
	subject   TEXT NOT NULL,
	attribute TEXT NOT NULL,
	value     TEXT NOT NULL,
	raw       TEXT
) STRICT;
`

// A Store is an open evidence database.
type Store struct {
	db *sql.DB
}

// Open opens the database at path, creating its tables if needed.
func Open(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	// One connection, so the foreign_keys setting applies to every statement.
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("create schema in %s: %w", path, err)
	}
	return &Store{db: db}, nil
}

// Close closes the database.
func (s *Store) Close() error { return s.db.Close() }

// Save writes a scan with its probes and observations, all or nothing, and
// returns the scan's id.
func (s *Store) Save(scan *collector.Scan) (int64, error) {
	tx, err := s.db.Begin()
	if err != nil {
		return 0, err
	}
	defer tx.Rollback() // no effect once committed

	res, err := tx.Exec(`INSERT INTO scans
		(kind, started_at, finished_at, tool_version, os, arch, connection_type)
		VALUES (?, ?, ?, ?, ?, ?, ?)`,
		scan.Kind, timestamp(scan.StartedAt), timestamp(scan.FinishedAt),
		collector.Version, runtime.GOOS, runtime.GOARCH, scan.ConnectionType)
	if err != nil {
		return 0, fmt.Errorf("insert scan: %w", err)
	}
	scanID, err := res.LastInsertId()
	if err != nil {
		return 0, err
	}

	// A probe is saved after the probe it ran during, which began first.
	ids := make(map[*collector.Probe]int64, len(scan.Probes))
	for _, p := range scan.Probes {
		id, err := insertProbe(tx, scanID, p, ids[p.ConcurrentWith])
		if err != nil {
			return 0, fmt.Errorf("insert probe %q: %w", p.Target, err)
		}
		ids[p] = id
	}
	return scanID, tx.Commit()
}

// insertProbe writes a probe and its observations. concurrentWith is the id
// of the probe it ran during, or 0.
func insertProbe(tx *sql.Tx, scanID int64, p *collector.Probe, concurrentWith int64) (int64, error) {
	res, err := tx.Exec(`INSERT INTO probes
		(scan_id, method, target, concurrent_with_probe_id, output, error, started_at, finished_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		scanID, p.Method, p.Target, nullableID(concurrentWith), nullable(p.Output), nullable(p.Err),
		timestamp(p.StartedAt), timestamp(p.FinishedAt))
	if err != nil {
		return 0, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return 0, err
	}
	for _, o := range p.Observations {
		if _, err := tx.Exec(`INSERT INTO observations (probe_id, subject, attribute, value, raw)
			VALUES (?, ?, ?, ?, ?)`, id, o.Subject, o.Attribute, o.Value, nullable(o.Raw)); err != nil {
			return 0, fmt.Errorf("observation %s.%s: %w", o.Subject, o.Attribute, err)
		}
	}
	return id, nil
}

func timestamp(t time.Time) string { return t.UTC().Format(timeFormat) }

// nullable stores an empty string as NULL.
func nullable(s string) sql.NullString { return sql.NullString{String: s, Valid: s != ""} }

// nullableID stores a zero id as NULL.
func nullableID(id int64) sql.NullInt64 { return sql.NullInt64{Int64: id, Valid: id != 0} }
