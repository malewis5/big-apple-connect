package collector

import (
	"strconv"
	"strings"
)

var linux = platform{
	route: func(r *recorder) (iface, gateway string) {
		obs := r.command(reading{parse: parseRouteLinux, keep: true}, "ip", "route", "show", "default")
		return find(obs, subjectHost, "interface_name"), find(obs, subjectGateway, "ip_address")
	},
	link: func(r *recorder, iface string) string {
		if iface == "" {
			return connectionUnknown
		}
		device := "/sys/class/net/" + iface
		obs := r.file(reading{parse: parseUevent, keep: true}, device+"/uevent")
		if reported := find(obs, subjectHost, "interface_type"); reported != "" {
			return connectionType(reported)
		}
		// A wired interface has no DEVTYPE but reports a negotiated speed.
		if obs := r.file(reading{parse: whole(subjectHost, "link_speed")}, device+"/speed"); len(obs) > 0 {
			return connectionEthernet
		}
		return connectionUnknown
	},
	radio: func(r *recorder, iface string) {
		r.command(reading{parse: labelled(map[string]string{
			"freq": "wifi_channel", "signal": "wifi_signal", "tx bitrate": "wifi_tx_rate",
		})}, "iw", "dev", iface, "link")
	},
	cpu: func(r *recorder, during *Probe) {
		r.file(reading{parse: whole(subjectHost, "cpu_load"), during: during}, "/proc/loadavg")
	},
	neighbor: func(ip string) []string { return []string{"ip", "neigh", "show", ip} },
	ping: func(host string, count int) []string {
		return []string{"ping", "-c", strconv.Itoa(count), "-i", pingInterval, "-w", pingDeadline(count), host}
	},
	trace:     []string{"traceroute", "-n", "-m", traceMaxHops, "-q", "1", "-w", "1", traceTarget},
	loadPings: 30,
}

// parseRouteLinux reads the first route from `ip route show default`:
//
//	default via 192.168.1.1 dev eth0 proto dhcp metric 100
func parseRouteLinux(text string) []Observation {
	var f facts
	for _, line := range lines(text) {
		fields := strings.Fields(line)
		if len(fields) < 3 || fields[0] != "default" || fields[1] != "via" {
			continue
		}
		f.add(subjectGateway, "ip_address", fields[2], line)
		for i := 3; i+1 < len(fields); i++ {
			if fields[i] == "dev" {
				f.add(subjectHost, "interface_name", fields[i+1], line)
			}
		}
		break
	}
	return f
}

// parseUevent reads an interface's uevent file. The kernel writes
// DEVTYPE=wlan for a wireless interface and no DEVTYPE for a wired one.
func parseUevent(text string) []Observation {
	var f facts
	for _, line := range lines(text) {
		if devtype, ok := strings.CutPrefix(line, "DEVTYPE="); ok {
			f.add(subjectHost, "interface_type", devtype, line)
		}
	}
	return f
}
