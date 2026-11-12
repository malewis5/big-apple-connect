// Command big-apple-connect collects evidence about a home internet
// connection and saves it to evidence.db. The same program runs on a
// dedicated box and as an app on a volunteer's own computer.
package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"text/tabwriter"
	"time"

	"github.com/malewis5/big-apple-connect/internal/collector"
	"github.com/malewis5/big-apple-connect/internal/store"
)

const (
	databasePath  = "evidence.db"
	lightInterval = 5 * time.Minute // Netrics' schedule for light measurements
	scansPerFull  = 12              // one full scan an hour
	maxTargetLen  = 44              // width of the report's target column
)

func main() {
	log.SetFlags(0)
	if err := run(); err != nil {
		log.Fatal(err)
	}
}

func run() error {
	kind := flag.String("kind", collector.KindFull, "scan to run once: full or light")
	daemon := flag.Bool("daemon", false, "keep running: a light scan every 5 minutes, a full scan every hour")
	flag.Parse()
	if *kind != collector.KindFull && *kind != collector.KindLight {
		return fmt.Errorf("unknown kind %q: use full or light", *kind)
	}

	db, err := store.Open(databasePath)
	if err != nil {
		return err
	}
	defer db.Close()

	if *daemon {
		runSchedule(db) // runs until the process is stopped
	}
	scan, err := runScan(db, *kind)
	report(os.Stdout, scan)
	return err
}

// runSchedule scans until the process is stopped: a full scan first and
// then every hour, a light scan every five minutes between.
func runSchedule(db *store.Store) {
	for n := 0; ; n++ {
		kind := collector.KindLight
		if n%scansPerFull == 0 {
			kind = collector.KindFull
		}
		started := time.Now()
		if _, err := runScan(db, kind); err != nil {
			log.Print(err)
		}
		time.Sleep(time.Until(started.Add(lightInterval)))
	}
}

// runScan performs one scan and saves it.
func runScan(db *store.Store, kind string) (*collector.Scan, error) {
	scan := collector.Run(kind)
	id, err := db.Save(scan)
	if err != nil {
		return scan, fmt.Errorf("save scan: %w", err)
	}
	fmt.Printf("scan %d (%s, %s) saved: %d probes\n", id, scan.Kind, scan.ConnectionType, len(scan.Probes))
	return scan, nil
}

// report prints a scan's observations, then the probes that found none.
func report(w io.Writer, scan *collector.Scan) {
	table := tabwriter.NewWriter(w, 0, 0, 2, ' ', 0)
	fmt.Fprintln(table, "\nSUBJECT\tATTRIBUTE\tVALUE\tTARGET")
	for _, p := range scan.Probes {
		for _, o := range p.Observations {
			fmt.Fprintf(table, "%s\t%s\t%s\t%s\n", o.Subject, o.Attribute, o.Value, describeTarget(p))
		}
	}
	fmt.Fprintln(table, "\nMETHOD\tTARGET\tERROR\t(probes that returned nothing readable)")
	for _, p := range scan.Probes {
		if len(p.Observations) == 0 {
			fmt.Fprintf(table, "%s\t%s\t%s\t\n", p.Method, p.Target, p.Err)
		}
	}
	table.Flush()
}

// describeTarget shortens a probe's target for the report and notes the
// probe it ran during.
func describeTarget(p *collector.Probe) string {
	target := p.Target
	if len(target) > maxTargetLen {
		target = target[:maxTargetLen-3] + "..."
	}
	if p.ConcurrentWith != nil {
		target += "  [during " + p.ConcurrentWith.Target + "]"
	}
	return target
}
