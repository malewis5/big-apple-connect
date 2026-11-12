package collector

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"

	"github.com/m-lab/ndt7-client-go"
	"github.com/m-lab/ndt7-client-go/spec"
)

// values indexes observations as "subject.attribute" -> value.
func values(observations []Observation) map[string]string {
	m := map[string]string{}
	for _, o := range observations {
		m[o.Subject+"."+o.Attribute] = o.Value
	}
	return m
}

// expect fails unless the parsed observations are exactly want.
func expect(t *testing.T, name string, observations []Observation, want map[string]string) {
	t.Helper()
	got := values(observations)
	if len(got) != len(want) {
		t.Errorf("%s: got %v, want %v", name, got, want)
		return
	}
	for k, v := range want {
		if got[k] != v {
			t.Errorf("%s: %s = %q, want %q", name, k, got[k], v)
		}
	}
}

// expectRawExcludes fails if any raw text holds one of the given strings.
func expectRawExcludes(t *testing.T, name string, observations []Observation, private ...string) {
	t.Helper()
	for _, o := range observations {
		for _, s := range private {
			if strings.Contains(o.Raw, s) {
				t.Errorf("%s: raw for %s holds %q", name, o.Attribute, s)
			}
		}
	}
}

func TestConnectionType(t *testing.T) {
	cases := map[string]string{
		"Wi-Fi": "WiFi", "Native 802.11": "WiFi", "Wireless LAN": "WiFi", "wlan": "WiFi",
		"Ethernet": "Ethernet", "Thunderbolt Ethernet": "Ethernet", "USB 10/100/1000 LAN": "Ethernet",
		" 802.3\r": "Ethernet",
		"":         "Unknown", "Thunderbolt Bridge": "Unknown", "iPhone USB": "Unknown",
		"Wireless WAN": "Unknown", "BlueTooth": "Unknown", "Unspecified": "Unknown",
	}
	for in, want := range cases {
		if got := connectionType(in); got != want {
			t.Errorf("connectionType(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestParseRoute(t *testing.T) {
	expect(t, "macOS", parseRouteDarwin("   route to: default\ndestination: default\n       mask: default\n    gateway: 192.168.1.254\n  interface: en0\n      flags: <UP,GATEWAY,DONE,STATIC,PRCLONING,GLOBAL>\n"),
		map[string]string{"gateway.ip_address": "192.168.1.254", "host.interface_name": "en0"})
	expect(t, "Linux", parseRouteLinux("default via 192.168.1.1 dev eth0 proto dhcp src 192.168.1.50 metric 100\ndefault via 192.168.1.1 dev wlan0 proto dhcp metric 600\n"),
		map[string]string{"gateway.ip_address": "192.168.1.1", "host.interface_name": "eth0"})
	expect(t, "Windows", parseRouteWindows("Active Routes:\r\nNetwork Destination        Netmask          Gateway       Interface  Metric\r\n          0.0.0.0          0.0.0.0      192.168.1.1     192.168.1.50     25\r\n"),
		map[string]string{"gateway.ip_address": "192.168.1.1"})
	expect(t, "no route", parseRouteLinux(""), map[string]string{})
}

func TestParseHardwarePorts(t *testing.T) {
	output := "\nHardware Port: Ethernet Adapter (en4)\nDevice: en4\nEthernet Address: 11:22:33:44:55:66\n\n" +
		"Hardware Port: Wi-Fi\nDevice: en0\nEthernet Address: aa:bb:cc:dd:ee:ff\n"
	obs := parseHardwarePorts("en0")(output)
	expect(t, "en0", obs, map[string]string{"host.interface_type": "Wi-Fi"})
	expectRawExcludes(t, "en0", obs, "Ethernet Address", "aa:bb")
	expect(t, "absent", parseHardwarePorts("en9")(output), map[string]string{})
}

func TestParseAirPort(t *testing.T) {
	output := "Wi-Fi:\n      Interfaces:\n        en0:\n          MAC Address: aa:bb:cc:dd:ee:ff\n" +
		"          Current Network Information:\n            HomeNetwork:\n              PHY Mode: 802.11n\n" +
		"              Channel: 1 (2GHz, 20MHz)\n              Security: WPA2 Personal\n" +
		"              Signal / Noise: -52 dBm / -91 dBm\n              Transmit Rate: 144\n" +
		"          Other Local Wi-Fi Networks:\n            NeighborNetwork:\n              PHY Mode: 802.11ax\n" +
		"              Channel: 149 (5GHz, 80MHz)\n              Signal / Noise: -70 dBm / -92 dBm\n"
	obs := parseAirPort(output)
	expect(t, "current network", obs, map[string]string{
		"host.wifi_phy_mode": "802.11n", "host.wifi_channel": "1 (2GHz, 20MHz)",
		"host.wifi_signal": "-52 dBm", "host.wifi_noise": "-91 dBm", "host.wifi_tx_rate": "144",
	})
	expectRawExcludes(t, "current network", obs, "HomeNetwork", "NeighborNetwork", "MAC Address")
}

func TestLabelled(t *testing.T) {
	parse := labelled(map[string]string{"Radio type": "wifi_phy_mode", "Signal": "wifi_signal"})
	obs := parse("    SSID                   : HomeNetwork\r\n    Physical address       : aa:bb:cc:dd:ee:ff\r\n" +
		"    Radio type             : 802.11ax\r\n    Signal                 : 80%\r\n")
	expect(t, "netsh", obs, map[string]string{"host.wifi_phy_mode": "802.11ax", "host.wifi_signal": "80%"})
	expectRawExcludes(t, "netsh", obs, "HomeNetwork", "aa:bb")
}

func TestParseUevent(t *testing.T) {
	expect(t, "wireless", parseUevent("DEVTYPE=wlan\nINTERFACE=wlan0\nIFINDEX=3\n"), map[string]string{"host.interface_type": "wlan"})
	expect(t, "wired", parseUevent("INTERFACE=eth0\nIFINDEX=2\n"), map[string]string{})
}

func TestParseNeighborAndOUI(t *testing.T) {
	cases := map[string]struct{ output, mac, oui string }{
		"macOS":    {"? (192.168.1.254) at a:1b:2c:3d:4e:5f on en0 ifscope [ethernet]\n", "a:1b:2c:3d:4e:5f", "0A:1B:2C"},
		"Linux":    {"192.168.1.1 dev eth0 lladdr 0a:1b:2c:3d:4e:5f REACHABLE\n", "0a:1b:2c:3d:4e:5f", "0A:1B:2C"},
		"Windows":  {"  192.168.1.1           0a-1b-2c-3d-4e-5f     dynamic\r\n", "0a-1b-2c-3d-4e-5f", "0A:1B:2C"},
		"no entry": {"192.168.1.254 (192.168.1.254) -- no entry\n", "", ""},
	}
	for name, c := range cases {
		mac := find(parseNeighbor(c.output), subjectGateway, "mac_address")
		if mac != c.mac || oui(mac) != c.oui {
			t.Errorf("%s: mac %q oui %q, want %q %q", name, mac, oui(mac), c.mac, c.oui)
		}
	}
}

func TestParseTrace(t *testing.T) {
	expect(t, "macOS", parseTrace(" 1  192.168.1.254  5.510 ms\n 2  203.0.113.1  30.284 ms\n 3  198.51.100.20  30.412 ms\n 4  *\n 5  1.1.1.1  28.662 ms\n"),
		map[string]string{
			"path.hop_1_ip_address": "192.168.1.254", "path.hop_2_ip_address": "203.0.113.1", "path.hop_3_ip_address": "198.51.100.20",
			"last_mile.ip_address": "203.0.113.1", "path.hops_to_target": "5",
		})
	// A second router: the first stop beyond the home network is the third.
	expect(t, "second router", parseTrace(" 1  192.168.68.1  2.1 ms\n 2  192.168.1.254  4.0 ms\n 3  203.0.113.1  30.2 ms\n"),
		map[string]string{
			"path.hop_1_ip_address": "192.168.68.1", "path.hop_2_ip_address": "192.168.1.254", "path.hop_3_ip_address": "203.0.113.1",
			"last_mile.ip_address": "203.0.113.1",
		})
	// A link-local first stop, as on a cloud machine, is not the last mile.
	expect(t, "link-local gateway", parseTrace(" 1  169.254.0.1  0.2 ms\n 2  203.0.113.1  1.1 ms\n"),
		map[string]string{"path.hop_1_ip_address": "169.254.0.1", "path.hop_2_ip_address": "203.0.113.1", "last_mile.ip_address": "203.0.113.1"})
	expect(t, "Windows", parseTrace("Tracing route to 1.1.1.1 over a maximum of 20 hops\r\n\r\n  1     2 ms     1 ms     1 ms  192.168.1.1\r\n  2    12 ms    11 ms    10 ms  203.0.113.1\r\n  3    11 ms    12 ms    11 ms  1.1.1.1\r\n\r\nTrace complete.\r\n"),
		map[string]string{
			"path.hop_1_ip_address": "192.168.1.1", "path.hop_2_ip_address": "203.0.113.1", "path.hop_3_ip_address": "1.1.1.1",
			"last_mile.ip_address": "203.0.113.1", "path.hops_to_target": "3",
		})
}

func TestPingParser(t *testing.T) {
	cases := map[string]struct {
		output string
		want   map[string]string
	}{
		"macOS": {
			"--- 192.168.1.254 ping statistics ---\n10 packets transmitted, 10 packets received, 0.0% packet loss\nround-trip min/avg/max/stddev = 48.344/95.260/174.920/43.035 ms\n",
			map[string]string{"gateway.packets_transmitted": "10", "gateway.packets_received": "10", "gateway.packet_loss_pct": "0.0",
				"gateway.rtt_min_ms": "48.344", "gateway.rtt_avg_ms": "95.260", "gateway.rtt_max_ms": "174.920", "gateway.rtt_mdev_ms": "43.035"},
		},
		"Linux": {
			"--- 1.1.1.1 ping statistics ---\n10 packets transmitted, 9 received, 10% packet loss, time 2254ms\nrtt min/avg/max/mdev = 3.100/4.200/6.000/0.900 ms\n",
			map[string]string{"gateway.packets_transmitted": "10", "gateway.packets_received": "9", "gateway.packet_loss_pct": "10",
				"gateway.rtt_min_ms": "3.100", "gateway.rtt_avg_ms": "4.200", "gateway.rtt_max_ms": "6.000", "gateway.rtt_mdev_ms": "0.900"},
		},
		"Windows": {
			"Ping statistics for 1.1.1.1:\r\n    Packets: Sent = 10, Received = 10, Lost = 0 (0% loss),\r\nApproximate round trip times in milli-seconds:\r\n    Minimum = 1ms, Maximum = 4ms, Average = 2ms\r\n",
			map[string]string{"gateway.packets_transmitted": "10", "gateway.packets_received": "10", "gateway.packet_loss_pct": "0",
				"gateway.rtt_min_ms": "1", "gateway.rtt_max_ms": "4", "gateway.rtt_avg_ms": "2"},
		},
		"all lost": {
			"10 packets transmitted, 0 packets received, 100.0% packet loss\n",
			map[string]string{"gateway.packets_transmitted": "10", "gateway.packets_received": "0", "gateway.packet_loss_pct": "100.0"},
		},
		"no summary": {"ping: cannot resolve nowhere.invalid: Unknown host\n", map[string]string{}},
	}
	for name, c := range cases {
		expect(t, name, pingParser(subjectGateway)(c.output), c.want)
	}
}

func TestParseIPInfo(t *testing.T) {
	obs, err := parseIPInfo(`{"ip":"203.0.113.9","city":"Anytown","org":"AS7018 AT&T Enterprises, LLC","loc":"0,0"}`)
	if err != nil {
		t.Fatal(err)
	}
	expect(t, "ipinfo", obs, map[string]string{"wan.public_ip": "203.0.113.9", "wan.asn": "7018", "wan.as_name": "AT&T Enterprises, LLC"})
	expectRawExcludes(t, "ipinfo", obs, "Anytown", "loc")
	if _, err := parseIPInfo("<html>"); err == nil {
		t.Error("text that is not JSON gave no error")
	}
}

func TestDevicePages(t *testing.T) {
	page, _ := url.Parse("http://192.168.1.254/cgi-bin/home.ha")
	front := `<html><meta http-equiv=Refresh content=0;url=/cgi-bin/home.ha><body></body></html>`
	home := `<a href="/cgi-bin/devices.ha">Devices</a><a href="/cgi-bin/sysinfo.ha">System</a><a href="http://example.com/about">Elsewhere</a>`
	if got := pageLinks(page, front); len(got) != 1 || got[0] != "http://192.168.1.254/cgi-bin/home.ha" {
		t.Errorf("redirect: got %v", got)
	}
	// The page listing other devices in the home is not followed.
	if got := pageLinks(page, home); len(got) != 1 || got[0] != "http://192.168.1.254/cgi-bin/sysinfo.ha" {
		t.Errorf("links: got %v", got)
	}

	info := "<tr><th width=\"50%\" scope=\"row\">Manufacturer</th>\n  <td width=\"50%\">ARRIS</td></tr>" +
		"<tr><th scope=\"row\">Model Number</th><td class=\"col2\">NVG589</td></tr>" +
		"<tr><th scope=\"row\">Serial Number</th><td class=\"col2\">SN123</td></tr>" +
		"<tr><th>Manufacturer:</th><td>Your device's manufacturer.</td></tr>"
	seen := map[string]bool{}
	expect(t, "fields", unseen(deviceFields(subjectGateway, info), seen),
		map[string]string{"gateway.manufacturer": "ARRIS", "gateway.model_number": "NVG589", "gateway.serial_number": "SN123"})
	expect(t, "fields already seen", unseen(deviceFields(subjectGateway, info), seen), map[string]string{})
}

// Some home equipment sends a whole page and then never ends the response.
// What arrived is returned together with the error.
func TestFetchKeepsWhatArrived(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, "<th>Model Number</th><td>NVG589</td>")
		w.(http.Flusher).Flush()
		<-r.Context().Done() // never end the response
	}))
	defer server.Close()

	res, err := fetch(&http.Client{Timeout: 200 * time.Millisecond}, server.URL)
	if err == nil {
		t.Fatal("a response that never ended gave no error")
	}
	if !res.answered() || res.status != "200 OK" {
		t.Fatalf("response = %+v", res)
	}
	expect(t, "partial page", deviceFields(subjectGateway, res.body), map[string]string{"gateway.model_number": "NVG589"})

	if res, err := fetch(&http.Client{Timeout: 200 * time.Millisecond}, "http://127.0.0.1:1/"); err == nil || res.answered() {
		t.Errorf("no server: response = %+v, err = %v", res, err)
	}
}

func TestParseDescription(t *testing.T) {
	obs, err := parseDescription(`<?xml version="1.0"?><root><device><friendlyName>Router</friendlyName>` +
		`<manufacturer>TP-Link</manufacturer><modelName>Archer BE550</modelName><serialNumber>SN123</serialNumber></device></root>`)
	if err != nil {
		t.Fatal(err)
	}
	expect(t, "description", obs, map[string]string{
		"gateway.manufacturer": "TP-Link", "gateway.model_name": "Archer BE550", "gateway.serial_number": "SN123"})
	if obs[1].Raw != "<modelName>Archer BE550</modelName>" {
		t.Errorf("raw = %q", obs[1].Raw)
	}
	if got := ssdpLocation("HTTP/1.1 200 OK\r\nCACHE-CONTROL: max-age=120\r\nLocation: http://192.168.1.1:1900/igd.xml\r\n\r\n"); got != "http://192.168.1.1:1900/igd.xml" {
		t.Errorf("location = %q", got)
	}
}

func TestNDT7Observations(t *testing.T) {
	// Counters from a real scan: 32,530,149 bytes in 11.06 s is 23.531 Mbit/s.
	download := &ndt7.LatestMeasurements{
		ConnectionInfo: &spec.ConnectionInfo{UUID: "uuid-down"},
		Client:         spec.Measurement{AppInfo: &spec.AppInfo{NumBytes: 32530149, ElapsedTime: 11059583}},
		Server:         spec.Measurement{TCPInfo: &spec.TCPInfo{}},
	}
	download.Server.TCPInfo.BytesSent = 588979
	download.Server.TCPInfo.BytesRetrans = 49609
	download.Server.TCPInfo.MinRTT = 28940
	expect(t, "download", downloadObservations("ndt.example.org", download), map[string]string{
		"internet.speedtest_ndt7_server": "ndt.example.org", "internet.speedtest_ndt7_downloaduuid": "uuid-down",
		"internet.speedtest_ndt7_download": "23.531", "internet.speedtest_ndt7_downloadretrans": "8.423",
		"internet.speedtest_ndt7_downloadlatency": "28.940",
	})

	// 117,872 bytes in 6.39 s is 0.147 Mbit/s.
	upload := &ndt7.LatestMeasurements{
		ConnectionInfo: &spec.ConnectionInfo{UUID: "uuid-up"},
		Server:         spec.Measurement{TCPInfo: &spec.TCPInfo{}},
	}
	upload.Server.TCPInfo.BytesReceived = 117872
	upload.Server.TCPInfo.ElapsedTime = 6393831
	upload.Server.TCPInfo.MinRTT = 88495
	obs := uploadObservations("", upload)
	expect(t, "upload", obs, map[string]string{
		"internet.speedtest_ndt7_uploaduuid": "uuid-up", "internet.speedtest_ndt7_upload": "0.147",
		"internet.speedtest_ndt7_uploadlatency": "88.495",
	})
	if raw := obs[1].Raw; raw != `{"BytesReceived":117872,"ElapsedTime":6393831}` {
		t.Errorf("upload raw = %s", raw)
	}

	expect(t, "no result", downloadObservations("ndt.example.org", nil), map[string]string{})
	expect(t, "no counters", uploadObservations("", &ndt7.LatestMeasurements{}), map[string]string{})
}

func TestFacts(t *testing.T) {
	var f facts
	f.add(subjectGateway, "rtt_avg_ms", " 95.260 ", "round-trip ...")
	f.add(subjectGateway, "rtt_max_ms", "  ", "a value that is empty once trimmed is not an observation")
	if len(f) != 1 || f[0].Value != "95.260" || find(f, subjectGateway, "rtt_avg_ms") != "95.260" || find(f, subjectHost, "rtt_avg_ms") != "" {
		t.Fatalf("facts = %+v", f)
	}
}

func TestPlatformsAreComplete(t *testing.T) {
	for name, p := range map[string]platform{"darwin": darwin, "linux": linux, "windows": windows} {
		if p.route == nil || p.link == nil || p.radio == nil || p.cpu == nil || p.neighbor == nil || p.ping == nil || len(p.trace) == 0 || p.loadPings == 0 {
			t.Errorf("%s is missing a step", name)
		}
	}
}
