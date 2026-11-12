// Package collector records evidence about a home internet connection: what
// the connection is (the setup) and how it performs (the measurements).
//
// It records what it did and what came back.
//
//   - A Scan is one run.
//   - A Probe is one thing the collector did: a command run, a page
//     requested, a test performed. It records when, and any error returned.
//   - An Observation is one fact read from a probe's response, with the
//     exact text it was read from.
//
// The only value the collector decides itself is Scan.ConnectionType.
//
// Every step has two halves. One half does something: runs a command or
// makes a request. The other half is a function from the text that came
// back to observations, with no side effects, so it can be tested against
// sample output from any operating system.
package collector

import (
	"net/http"
	"runtime/debug"
	"time"
)

// version is set when a release is built:
//
//	go build -ldflags "-X github.com/malewis5/big-apple-connect-box/apps/box/internal/collector.version=v0.0.2"
var version string

// Version returns the collector's version, stored with every scan: the
// release it was built as, else the version Go recorded for the build, else
// "devel".
func Version() string {
	if version != "" {
		return version
	}
	if info, ok := debug.ReadBuildInfo(); ok && info.Main.Version != "" && info.Main.Version != "(devel)" {
		return info.Main.Version
	}
	return "devel"
}

// Scan kinds. The schedule follows Netrics: light measurements every five
// minutes, the speed test hourly.
const (
	KindLight = "light" // connection, route, pings, name lookups
	KindFull  = "full"  // light, plus equipment, public address and speed test
)

// Subjects: what an observation is about.
const (
	subjectHost     = "host"      // this computer
	subjectWAN      = "wan"       // the line's public side
	subjectGateway  = "gateway"   // the router this computer talks to
	subjectModem    = "modem"     // the modem, where separate
	subjectPath     = "path"      // the route out
	subjectLastMile = "last_mile" // the provider's first stop outside the home
	subjectInternet = "internet"  // points beyond it
)

// Methods: how a probe was made.
const (
	methodExec       = "exec"
	methodHTTPGet    = "http_get"
	methodDNSPTR     = "dns_ptr"
	methodDNSQuery   = "dns_query"
	methodSSDPSearch = "ssdp_search"
	methodFileRead   = "file_read"
	methodNDT7       = "ndt7"
)

// Connection types.
const (
	connectionEthernet = "Ethernet"
	connectionWiFi     = "WiFi"
	connectionUnknown  = "Unknown"
)

// An Observation is one fact read from a probe's response. Raw is the exact
// text the value was read from. Raw is empty when the collector measured the
// value itself, such as a duration it timed.
type Observation struct {
	Subject   string
	Attribute string
	Value     string
	Raw       string
}

// A Probe is one thing the collector did.
type Probe struct {
	Method         string
	Target         string // the command, address, file or test
	ConcurrentWith *Probe // the probe this one deliberately ran during
	StartedAt      time.Time
	FinishedAt     time.Time
	Output         string // the response, kept when nothing could be read from it
	Err            string // the error returned, word for word
	Observations   []Observation
}

// A Scan is one run.
type Scan struct {
	Kind           string
	ConnectionType string // Ethernet, WiFi or Unknown
	StartedAt      time.Time
	FinishedAt     time.Time
	Probes         []*Probe
}

// collector holds what one scan needs: where probes are recorded, how this
// operating system is asked questions, and the two network clients.
type collector struct {
	*recorder
	os  platform
	lan *http.Client // for equipment on the home network
	wan *http.Client // for services on the internet
}

// Run performs one scan of the given kind.
func Run(kind string) *Scan {
	c := &collector{
		recorder: &recorder{},
		os:       hostPlatform(),
		lan:      newLANClient(),
		wan:      &http.Client{Timeout: wanTimeout},
	}
	scan := &Scan{Kind: kind, StartedAt: time.Now().UTC()}

	// The setup.
	iface, gateway := c.os.route(c.recorder)
	scan.ConnectionType = c.os.link(c.recorder, iface)
	if kind == KindFull {
		c.wanIdentity()
		c.gateway(gateway)
		c.modem(gateway)
	}

	// The measurements.
	lastMile := c.path()
	c.pings(gateway, lastMile)
	c.dns()
	if kind == KindFull {
		c.ndt7(gateway)
	}

	// Read last: reading radio details can make the radio scan, which would
	// disturb a measurement taken at the same time.
	if scan.ConnectionType == connectionWiFi {
		c.os.radio(c.recorder, iface)
	}

	scan.Probes = c.probes()
	scan.FinishedAt = time.Now().UTC()
	return scan
}
