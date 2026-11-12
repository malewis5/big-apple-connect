package store

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/malewis5/big-apple-connect-box/apps/box/internal/collector"
)

func TestSave(t *testing.T) {
	s, err := Open(filepath.Join(t.TempDir(), "evidence.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()

	at := time.Date(2026, 11, 12, 19, 31, 32, 370_000_000, time.UTC)
	speed := &collector.Probe{Method: "ndt7", Target: "download", StartedAt: at, FinishedAt: at.Add(13 * time.Second),
		Observations: []collector.Observation{{Subject: "internet", Attribute: "speedtest_ndt7_download", Value: "23.531", Raw: `{"NumBytes":1}`}}}
	ping := &collector.Probe{Method: "exec", Target: "ping gateway", ConcurrentWith: speed, StartedAt: at, FinishedAt: at.Add(7 * time.Second),
		Observations: []collector.Observation{{Subject: "gateway", Attribute: "rtt_avg_ms", Value: "67.362", Raw: "round-trip ..."}}}
	timed := &collector.Probe{Method: "dns_query", Target: "www.google.com", StartedAt: at, FinishedAt: at,
		Observations: []collector.Observation{{Subject: "internet", Attribute: "dns_query_time_ms", Value: "59.646"}}}
	failed := &collector.Probe{Method: "http_get", Target: "http://192.168.100.1/", Err: "timeout", StartedAt: at, FinishedAt: at.Add(4 * time.Second)}
	scan := &collector.Scan{Kind: collector.KindFull, ConnectionType: "WiFi", StartedAt: at, FinishedAt: at.Add(time.Minute),
		Probes: []*collector.Probe{speed, ping, timed, failed}}

	scanID, err := s.Save(scan)
	if err != nil {
		t.Fatal(err)
	}

	count := func(query string, args ...any) (n int) {
		t.Helper()
		if err := s.db.QueryRow(query, args...).Scan(&n); err != nil {
			t.Fatalf("%s: %v", query, err)
		}
		return n
	}
	checks := map[string]struct {
		got, want int
	}{
		"probes":                     {count(`SELECT count(*) FROM probes WHERE scan_id = ?`, scanID), 4},
		"observations":               {count(`SELECT count(*) FROM observations`), 3},
		"probes during the download": {count(`SELECT count(*) FROM probes WHERE concurrent_with_probe_id = (SELECT id FROM probes WHERE target = 'download')`), 1},
		"probes during nothing":      {count(`SELECT count(*) FROM probes WHERE concurrent_with_probe_id IS NULL`), 3},
		"observations without raw":   {count(`SELECT count(*) FROM observations WHERE raw IS NULL`), 1},
		"probes with an error":       {count(`SELECT count(*) FROM probes WHERE error = 'timeout' AND output IS NULL`), 1},
	}
	for name, c := range checks {
		if c.got != c.want {
			t.Errorf("%s = %d, want %d", name, c.got, c.want)
		}
	}

	var connection, version, started string
	if err := s.db.QueryRow(`SELECT connection_type, tool_version, started_at FROM scans WHERE id = ?`, scanID).
		Scan(&connection, &version, &started); err != nil {
		t.Fatal(err)
	}
	if connection != "WiFi" || version != collector.Version() || started != "2026-11-12T19:31:32.370Z" {
		t.Errorf("scan = %q %q %q", connection, version, started)
	}
}

func TestSaveIsAllOrNothing(t *testing.T) {
	s, err := Open(filepath.Join(t.TempDir(), "evidence.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()

	// The database accepts Ethernet, WiFi and Unknown.
	scan := &collector.Scan{Kind: collector.KindLight, ConnectionType: "Cable",
		Probes: []*collector.Probe{{Method: "exec", Target: "example"}}}
	if _, err := s.Save(scan); err == nil {
		t.Fatal("a connection type outside Ethernet, WiFi, Unknown was accepted")
	}
	var scans int
	if err := s.db.QueryRow(`SELECT count(*) FROM scans`).Scan(&scans); err != nil || scans != 0 {
		t.Fatalf("scans = %d, err = %v; want none saved", scans, err)
	}
}
