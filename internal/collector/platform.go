package collector

import (
	"runtime"
	"strings"
)

// A platform is how one operating system is asked about this computer's
// connection. Each is defined once, in darwin.go, linux.go and windows.go;
// nothing else in the package depends on the operating system.
type platform struct {
	// route reports the interface carrying this computer's traffic and the
	// gateway's address.
	route func(r *recorder) (iface, gateway string)

	// link reports whether that interface is Ethernet, WiFi or Unknown,
	// recording the operating system's own word and a wired link's speed.
	link func(r *recorder, iface string) (connectionType string)

	// radio records the Wi-Fi link's standard, channel, signal and rate.
	radio func(r *recorder, iface string)

	// cpu records the processor load, alongside the given probe.
	cpu func(r *recorder, during *Probe)

	// neighbor is the command that prints the hardware address for an
	// address on the home network.
	neighbor func(ip string) []string

	// ping is the command that sends count pings to host.
	ping func(host string, count int) []string

	// trace is the command that traces the route to traceTarget.
	trace []string

	// loadPings is how many pings span most of one speed-test phase.
	loadPings int
}

func hostPlatform() platform {
	switch runtime.GOOS {
	case "darwin":
		return darwin
	case "windows":
		return windows
	default:
		return linux
	}
}

// connectionType reduces the operating system's description of a network
// interface to Ethernet, WiFi or Unknown.
//
//	macOS    Hardware Port      "Wi-Fi", "Ethernet", "USB 10/100/1000 LAN"
//	Windows  PhysicalMediaType  "Native 802.11", "Wireless LAN", "802.3"
//	Linux    DEVTYPE            "wlan"
func connectionType(reported string) string {
	r := strings.ToLower(strings.TrimSpace(reported))
	switch {
	case strings.Contains(r, "wi-fi"), strings.Contains(r, "802.11"), strings.Contains(r, "wireless lan"), r == "wlan":
		return connectionWiFi
	case strings.Contains(r, "ethernet"), strings.Contains(r, "802.3"), strings.HasSuffix(r, " lan"):
		return connectionEthernet
	default:
		return connectionUnknown
	}
}
