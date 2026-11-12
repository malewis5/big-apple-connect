package collector

// The measurements: how the connection performs. What is measured, and how,
// follows Netrics (github.com/internet-innovation/netrics) so results are
// comparable with its deployments:
//
//	ping        10 pings a quarter second apart, 5 second deadline
//	last mile   trace the route, then ping the first stop that is not a
//	            home-network address
//	dns         time name lookups against 8.8.8.8
//	hops        count the stops to the trace target
//	speed       NDT7, computed as M-Lab's own client computes it
//
// Ping and speed-test attributes carry Netrics' result names.
//
// One addition: the gateway is pinged too, both idle and during the speed
// test. Netrics has no need for it because its box is always wired in.

import (
	"context"
	"encoding/json"
	"net"
	"regexp"
	"strconv"
	"sync"
	"time"

	"github.com/m-lab/ndt7-client-go"
	"github.com/m-lab/ndt7-client-go/spec"
)

const (
	traceTarget  = "1.1.1.1" // Netrics' last-mile trace target
	traceMaxHops = "20"
	pathHops     = 3 // stops recorded from the start of the route

	pingCount    = 10     // Netrics' count
	pingInterval = "0.25" // Netrics' interval, in seconds

	dnsServer  = "8.8.8.8:53" // Netrics' name-lookup server
	dnsTimeout = 5 * time.Second

	ndt7ClientName = "big-apple-connect"
	ndt7Timeout    = 90 * time.Second
	// cpuSampleDelay puts the processor-load reading inside the download.
	cpuSampleDelay = 3 * time.Second
)

var (
	// Destinations from Netrics' defaults that are not specific to Chicago.
	pingDestinations = []string{"1.1.1.1", "8.8.8.8", "www.google.com"}
	dnsNames         = []string{"www.google.com", "www.amazon.com", "www.wikipedia.org", "www.youtube.com", "www.facebook.com"}

	ipv4Pattern = regexp.MustCompile(`\b(\d{1,3}\.){3}\d{1,3}\b`)
	hopPattern  = regexp.MustCompile(`^\s*(\d+)\s`)

	// macOS: 10 packets transmitted, 10 packets received, 0.0% packet loss
	// Linux: 10 packets transmitted, 10 received, 0% packet loss, time 2254ms
	// Windows: Packets: Sent = 10, Received = 10, Lost = 0 (0% loss),
	pingCountsPatterns = []*regexp.Regexp{
		regexp.MustCompile(`(\d+) packets transmitted, (\d+) (?:packets )?received.*?([\d.]+)% packet loss`),
		regexp.MustCompile(`Sent = (\d+), Received = (\d+), Lost = \d+ \((\d+)% loss\)`),
	}
	// macOS: round-trip min/avg/max/stddev = 3.1/4.2/6.0/0.9 ms
	// Linux: rtt min/avg/max/mdev = 3.1/4.2/6.0/0.9 ms
	pingRTTPattern = regexp.MustCompile(`(?:round-trip|rtt) min/avg/max/(?:stddev|mdev) = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms`)
	// Windows: Minimum = 1ms, Maximum = 4ms, Average = 2ms
	pingWindowsRTTPattern = regexp.MustCompile(`Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms`)
)

// ---- path: the route out, and the provider's first stop ----

// path traces the route and returns the last-mile address.
func (c *collector) path() (lastMile string) {
	obs := c.command(reading{parse: parseTrace, keep: true}, c.os.trace...)
	return find(obs, subjectLastMile, "ip_address")
}

// parseTrace reads a route trace: the first stops, the last-mile stop (the
// first that is not a home-network address) and the number of stops to the
// target.
//
//	macOS, Linux:   1  192.168.1.254  5.510 ms
//	Windows:        1     2 ms     1 ms     1 ms  192.168.1.254
func parseTrace(text string) []Observation {
	var f facts
	foundLastMile := false
	for _, line := range lines(text) {
		m := hopPattern.FindStringSubmatch(line)
		if m == nil {
			continue
		}
		hop, ip := m[1], ipv4Pattern.FindString(line)
		if n, _ := strconv.Atoi(hop); n <= pathHops {
			f.add(subjectPath, "hop_"+hop+"_ip_address", ip, line)
		}
		if !foundLastMile && outsideHome(ip) {
			foundLastMile = true
			f.add(subjectLastMile, "ip_address", ip, line)
		}
		if ip == traceTarget {
			f.add(subjectPath, "hops_to_target", hop, line)
		}
	}
	return f
}

// outsideHome reports whether ip is an address beyond the home network:
// not a private, link-local or loopback address. This is the rule Netrics
// applies to find the last-mile stop.
func outsideHome(ip string) bool {
	parsed := net.ParseIP(ip)
	return parsed != nil && !parsed.IsPrivate() && !parsed.IsLinkLocalUnicast() && !parsed.IsLoopback()
}

// ---- ping ----

// pings pings the gateway, the last-mile stop and the internet destinations
// at the same time, as Netrics does.
func (c *collector) pings(gateway, lastMile string) {
	targets := []struct{ subject, host string }{
		{subjectGateway, gateway},
		{subjectLastMile, lastMile},
	}
	for _, host := range pingDestinations {
		targets = append(targets, struct{ subject, host string }{subjectInternet, host})
	}

	var wg sync.WaitGroup
	for _, t := range targets {
		if t.host != "" {
			wg.Go(func() { c.ping(t.subject, t.host, pingCount, nil) })
		}
	}
	wg.Wait()
}

func (c *collector) ping(subject, host string, count int, during *Probe) {
	c.command(reading{parse: pingParser(subject), keep: true, during: during}, c.os.ping(host, count)...)
}

// pingDeadline is how long, in seconds, a run of count pings may take:
// Netrics' five seconds, plus the time the pings themselves span.
func pingDeadline(count int) string { return strconv.Itoa(5 + count/4) }

// pingParser returns a parser for the summary the system's ping prints.
func pingParser(subject string) parser {
	return func(text string) []Observation {
		var f facts
		for _, line := range lines(text) {
			for _, pattern := range pingCountsPatterns {
				if m := pattern.FindStringSubmatch(line); m != nil {
					f.add(subject, "packets_transmitted", m[1], line)
					f.add(subject, "packets_received", m[2], line)
					f.add(subject, "packet_loss_pct", m[3], line)
				}
			}
			if m := pingRTTPattern.FindStringSubmatch(line); m != nil {
				f.add(subject, "rtt_min_ms", m[1], line)
				f.add(subject, "rtt_avg_ms", m[2], line)
				f.add(subject, "rtt_max_ms", m[3], line)
				f.add(subject, "rtt_mdev_ms", m[4], line)
			}
			if m := pingWindowsRTTPattern.FindStringSubmatch(line); m != nil {
				f.add(subject, "rtt_min_ms", m[1], line)
				f.add(subject, "rtt_max_ms", m[2], line)
				f.add(subject, "rtt_avg_ms", m[3], line)
			}
		}
		return f
	}
}

// ---- dns ----

// dns times one lookup of each name against a fixed public server. The
// time is measured by the collector, so these observations have no raw
// text.
func (c *collector) dns() {
	resolver := &net.Resolver{
		PreferGo: true,
		Dial: func(ctx context.Context, network, _ string) (net.Conn, error) {
			return (&net.Dialer{}).DialContext(ctx, network, dnsServer)
		},
	}
	for _, name := range dnsNames {
		p := c.begin(methodDNSQuery, name+" @"+dnsServer)
		elapsed, err := timeLookup(resolver, name)
		if err == nil {
			var f facts
			f.add(subjectInternet, "dns_query_time_ms", decimal(float64(elapsed.Microseconds())/1000), "")
			p.Observations = f
		}
		p.end(err)
	}
}

func timeLookup(resolver *net.Resolver, name string) (time.Duration, error) {
	ctx, cancel := context.WithTimeout(context.Background(), dnsTimeout)
	defer cancel()
	start := time.Now()
	// The trailing dot stops the resolver trying the home network's own
	// domain first.
	_, err := resolver.LookupIP(ctx, "ip4", name+".")
	return time.Since(start), err
}

// ---- speed test ----

// A phase is one direction of the NDT7 test.
type phase struct {
	test      spec.TestKind
	start     func(context.Context) (<-chan spec.Measurement, error)
	read      func(server string, result *ndt7.LatestMeasurements) []Observation
	sampleCPU bool
}

// ndt7 runs an NDT7 download and upload. While each runs, it pings the
// gateway, and during the download it also reads the processor load, so
// the home's side of the connection is on record for the same seconds.
func (c *collector) ndt7(gateway string) {
	client := ndt7.NewClient(ndt7ClientName, Version)
	ctx, cancel := context.WithTimeout(context.Background(), ndt7Timeout)
	defer cancel()

	for _, ph := range []phase{
		{test: spec.TestDownload, start: client.StartDownload, read: downloadObservations, sampleCPU: true},
		{test: spec.TestUpload, start: client.StartUpload, read: uploadObservations},
	} {
		p := c.begin(methodNDT7, string(ph.test))

		var alongside sync.WaitGroup
		if gateway != "" {
			alongside.Go(func() { c.ping(subjectGateway, gateway, c.os.loadPings, p) })
		}
		if ph.sampleCPU {
			alongside.Go(func() { time.Sleep(cpuSampleDelay); c.os.cpu(c.recorder, p) })
		}

		measurements, err := ph.start(ctx)
		if err == nil {
			for range measurements { // drain until the phase ends
			}
			p.Observations = ph.read(client.FQDN, client.Results()[ph.test])
		}
		p.end(err)
		alongside.Wait()
	}
}

// downloadObservations computes download results as M-Lab's own client
// does: speed from the bytes this computer received, retransmission and
// round-trip time from the server's counters. Raw holds those counters.
func downloadObservations(server string, r *ndt7.LatestMeasurements) []Observation {
	var f facts
	if r == nil {
		return f
	}
	f.add(subjectInternet, "speedtest_ndt7_server", server, server)
	if c := r.ConnectionInfo; c != nil {
		f.add(subjectInternet, "speedtest_ndt7_downloaduuid", c.UUID, c.UUID)
	}
	if a := r.Client.AppInfo; a != nil && a.ElapsedTime > 0 {
		f.add(subjectInternet, "speedtest_ndt7_download", megabits(a.NumBytes, a.ElapsedTime),
			counters(map[string]int64{"NumBytes": a.NumBytes, "ElapsedTime": a.ElapsedTime}))
	}
	t := r.Server.TCPInfo
	if t == nil {
		return f
	}
	if t.BytesSent > 0 {
		f.add(subjectInternet, "speedtest_ndt7_downloadretrans", decimal(float64(t.BytesRetrans)/float64(t.BytesSent)*100),
			counters(map[string]int64{"BytesRetrans": t.BytesRetrans, "BytesSent": t.BytesSent}))
	}
	f.add(subjectInternet, "speedtest_ndt7_downloadlatency", decimal(float64(t.MinRTT)/1000),
		counters(map[string]int64{"MinRTT": int64(t.MinRTT)}))
	return f
}

// uploadObservations computes upload results as M-Lab's own client does:
// speed and round-trip time from the server's counters.
func uploadObservations(_ string, r *ndt7.LatestMeasurements) []Observation {
	var f facts
	if r == nil {
		return f
	}
	if c := r.ConnectionInfo; c != nil {
		f.add(subjectInternet, "speedtest_ndt7_uploaduuid", c.UUID, c.UUID)
	}
	t := r.Server.TCPInfo
	if t == nil {
		return f
	}
	if t.ElapsedTime > 0 {
		f.add(subjectInternet, "speedtest_ndt7_upload", megabits(t.BytesReceived, t.ElapsedTime),
			counters(map[string]int64{"BytesReceived": t.BytesReceived, "ElapsedTime": t.ElapsedTime}))
	}
	f.add(subjectInternet, "speedtest_ndt7_uploadlatency", decimal(float64(t.MinRTT)/1000),
		counters(map[string]int64{"MinRTT": int64(t.MinRTT)}))
	return f
}

// megabits returns the rate in Mbit/s of bytes moved in a time given in
// microseconds.
func megabits(bytes, microseconds int64) string {
	return decimal(8 * float64(bytes) / (float64(microseconds) / 1e6) / 1e6)
}

func counters(v map[string]int64) string {
	b, _ := json.Marshal(v) // a map of integers always marshals
	return string(b)
}

func decimal(v float64) string { return strconv.FormatFloat(v, 'f', 3, 64) }
