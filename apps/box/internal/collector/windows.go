package collector

import (
	"strconv"
	"strings"
)

const (
	// adapterScript prints the name, media type and speed of the adapter
	// carrying the default route. It selects those three properties because
	// the adapter's other properties include its hardware address.
	adapterScript = "$i = (Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Sort-Object RouteMetric | Select-Object -First 1).ifIndex; " +
		"Get-NetAdapter -InterfaceIndex $i | Format-List Name, PhysicalMediaType, LinkSpeed"

	loadScript = "(Get-CimInstance Win32_Processor).LoadPercentage"
)

var windows = platform{
	route: func(r *recorder) (iface, gateway string) {
		obs := r.command(reading{parse: parseRouteWindows, keep: true}, "route", "print", "-4", "0.0.0.0")
		return "", find(obs, subjectGateway, "ip_address")
	},
	link: func(r *recorder, _ string) string {
		obs := r.command(reading{parse: labelled(map[string]string{
			"Name": "interface_name", "PhysicalMediaType": "interface_type", "LinkSpeed": "link_speed",
		}), keep: true}, powershell(adapterScript)...)
		return connectionType(find(obs, subjectHost, "interface_type"))
	},
	radio: func(r *recorder, _ string) {
		r.command(reading{parse: labelled(map[string]string{
			"Radio type": "wifi_phy_mode", "Channel": "wifi_channel", "Signal": "wifi_signal",
			"Rssi": "wifi_signal", "Transmit rate (Mbps)": "wifi_tx_rate",
		})}, "netsh", "wlan", "show", "interfaces")
	},
	cpu: func(r *recorder, during *Probe) {
		r.command(reading{parse: whole(subjectHost, "cpu_load"), during: during}, powershell(loadScript)...)
	},
	neighbor: func(ip string) []string { return []string{"arp", "-a", ip} },
	// Windows pings once a second and has no interval option.
	ping: func(host string, count int) []string {
		return []string{"ping", "-n", strconv.Itoa(count), "-w", "1000", host}
	},
	trace:     []string{"tracert", "-d", "-h", traceMaxHops, "-w", "1000", traceTarget},
	loadPings: 8,
}

func powershell(script string) []string {
	return []string{"powershell", "-NoProfile", "-Command", script}
}

// parseRouteWindows reads the first default route from
// `route print -4 0.0.0.0`:
//
//	Network Destination        Netmask          Gateway       Interface  Metric
//	          0.0.0.0          0.0.0.0      192.168.1.1    192.168.1.50      25
func parseRouteWindows(text string) []Observation {
	var f facts
	for _, line := range lines(text) {
		fields := strings.Fields(line)
		if len(fields) >= 3 && fields[0] == "0.0.0.0" && fields[1] == "0.0.0.0" {
			f.add(subjectGateway, "ip_address", fields[2], line)
			break
		}
	}
	return f
}
