package collector

import (
	"strconv"
	"strings"
)

var darwin = platform{
	route: func(r *recorder) (iface, gateway string) {
		obs := r.command(reading{parse: parseRouteDarwin, keep: true}, "route", "-n", "get", "default")
		return find(obs, subjectHost, "interface_name"), find(obs, subjectGateway, "ip_address")
	},
	link: func(r *recorder, iface string) string {
		if iface == "" {
			return connectionUnknown
		}
		obs := r.command(reading{parse: parseHardwarePorts(iface)}, "networksetup", "-listallhardwareports")
		connection := connectionType(find(obs, subjectHost, "interface_type"))
		if connection == connectionEthernet {
			r.command(reading{parse: labelled(map[string]string{"media": "link_speed"})}, "ifconfig", iface)
		}
		return connection
	},
	radio: func(r *recorder, _ string) {
		r.command(reading{parse: parseAirPort}, "system_profiler", "SPAirPortDataType")
	},
	cpu: func(r *recorder, during *Probe) {
		r.command(reading{parse: whole(subjectHost, "cpu_load"), during: during}, "sysctl", "-n", "vm.loadavg")
	},
	neighbor: func(ip string) []string { return []string{"arp", "-n", ip} },
	ping: func(host string, count int) []string {
		return []string{"ping", "-c", strconv.Itoa(count), "-i", pingInterval, "-t", pingDeadline(count), host}
	},
	trace:     []string{"traceroute", "-n", "-m", traceMaxHops, "-q", "1", "-w", "1", traceTarget},
	loadPings: 30,
}

// parseRouteDarwin reads `route -n get default`:
//
//	  gateway: 192.168.1.254
//	interface: en0
func parseRouteDarwin(text string) []Observation {
	var f facts
	for _, line := range lines(text) {
		switch label, value, _ := strings.Cut(line, ":"); strings.TrimSpace(label) {
		case "gateway":
			f.add(subjectGateway, "ip_address", value, line)
		case "interface":
			f.add(subjectHost, "interface_name", value, line)
		}
	}
	return f
}

// parseHardwarePorts reads `networksetup -listallhardwareports` for one
// interface:
//
//	Hardware Port: Wi-Fi
//	Device: en0
//	Ethernet Address: ...
//
// It keeps the first two lines. The third is this computer's own hardware
// address.
func parseHardwarePorts(iface string) parser {
	return func(text string) []Observation {
		var f facts
		all := lines(text)
		for i := 1; i < len(all); i++ {
			port, isPort := strings.CutPrefix(all[i-1], "Hardware Port: ")
			if isPort && strings.TrimSpace(all[i]) == "Device: "+iface {
				f.add(subjectHost, "interface_type", port, all[i-1]+"\n"+all[i])
			}
		}
		return f
	}
}

// parseAirPort reads the radio details of the current network from
// `system_profiler SPAirPortDataType`. The report also holds the network's
// name and every nearby network; only these lines are kept:
//
//	PHY Mode: 802.11n
//	Channel: 1 (2GHz, 20MHz)
//	Signal / Noise: -52 dBm / -91 dBm
//	Transmit Rate: 144
func parseAirPort(text string) []Observation {
	var f facts
	current := false
	for _, line := range lines(text) {
		label, value, _ := strings.Cut(line, ":")
		switch label = strings.TrimSpace(label); {
		case label == "Current Network Information":
			current = true
		case label == "Other Local Wi-Fi Networks":
			current = false
		case !current:
		case label == "PHY Mode":
			f.add(subjectHost, "wifi_phy_mode", value, line)
		case label == "Channel":
			f.add(subjectHost, "wifi_channel", value, line)
		case label == "Transmit Rate":
			f.add(subjectHost, "wifi_tx_rate", value, line)
		case label == "Signal / Noise":
			signal, noise, _ := strings.Cut(value, "/")
			f.add(subjectHost, "wifi_signal", signal, line)
			f.add(subjectHost, "wifi_noise", noise, line)
		}
	}
	return f
}
