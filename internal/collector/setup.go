package collector

// The setup, beyond this computer's own link: the provider, the gateway and
// the modem. These steps are the same on every operating system.

import (
	"crypto/tls"
	"encoding/json"
	"encoding/xml"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
)

const (
	ipinfoEndpoint = "https://ipinfo.io/json"
	ouiEndpoint    = "https://api.macvendors.com/"

	// Cable modems conventionally answer here, on their own network.
	modemURL     = "http://192.168.100.1/"
	modemNetwork = "192.168.100."

	ssdpAddress = "239.255.255.250:1900"
	ssdpSearch  = "M-SEARCH * HTTP/1.1\r\nHOST: " + ssdpAddress + "\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\nST: upnp:rootdevice\r\n\r\n"
	ssdpWait    = 3 * time.Second

	lanTimeout   = 4 * time.Second
	wanTimeout   = 6 * time.Second
	maxBodyBytes = 512 << 10
	maxPages     = 5 // a device's front page and up to four more
)

var (
	macPattern     = regexp.MustCompile(`\b([0-9A-Fa-f]{1,2}[:-]){5}[0-9A-Fa-f]{1,2}\b`)
	asnPattern     = regexp.MustCompile(`^AS(\d+)\s+(.*)$`)
	refreshPattern = regexp.MustCompile(`(?i)http-equiv=["']?refresh["']?[^>]*url=([^"'>\s]+)`)
	hrefPattern    = regexp.MustCompile(`(?i)href=["']([^"'#]+)["']`)
	// Pages likely to describe the device itself. Deliberately excludes
	// pages listing other devices in the home.
	infoPagePattern = regexp.MustCompile(`(?i)(sys(tem)?_?info|device_?info|about)`)
	// A labelled table row: <th>Model Number</th><td>NVG589</td>.
	labelPattern = regexp.MustCompile(`(?is)<t[hd][^>]*>\s*(manufacturer|model\s+number|model\s+name|model|serial\s+number)\s*:?\s*</t[hd]>\s*<td[^>]*>\s*([^<]{1,64}?)\s*</td>`)
)

// newLANClient returns a client for equipment on the home network, which
// often uses self-signed certificates.
func newLANClient() *http.Client {
	return &http.Client{
		Timeout:   lanTimeout,
		Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}},
	}
}

// A response is what a page request returned.
type response struct {
	status string   // the server's status line, for example "200 OK"
	url    *url.URL // the address after redirects
	body   string
}

// answered reports whether the server replied at all.
func (r response) answered() bool { return r.status != "" }

// fetch requests a page. When the server replied but its body could not be
// read to the end, fetch returns what arrived together with the error:
// some home equipment sends a whole page and then never ends the response.
func fetch(client *http.Client, rawURL string) (response, error) {
	resp, err := client.Get(rawURL)
	if err != nil {
		return response{}, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, maxBodyBytes))
	return response{status: resp.Status, url: resp.Request.URL, body: string(body)}, err
}

// ---- wan: the line's public address and who it is registered to ----

func (c *collector) wanIdentity() {
	p := c.begin(methodHTTPGet, ipinfoEndpoint)
	res, err := fetch(c.wan, ipinfoEndpoint)
	if err == nil {
		p.Observations, err = parseIPInfo(res.body)
	}
	p.end(err)

	if ip := find(p.Observations, subjectWAN, "public_ip"); ip != "" {
		c.ptr(subjectWAN, ip)
	}
}

// parseIPInfo reads the public address and its registered network from
// ipinfo.io's JSON, where org is "AS7018 AT&T Enterprises, LLC".
func parseIPInfo(body string) ([]Observation, error) {
	var v struct{ IP, Org string }
	if err := json.Unmarshal([]byte(body), &v); err != nil {
		return nil, err
	}
	var f facts
	f.add(subjectWAN, "public_ip", v.IP, v.IP)
	if m := asnPattern.FindStringSubmatch(v.Org); m != nil {
		f.add(subjectWAN, "asn", m[1], v.Org)
		f.add(subjectWAN, "as_name", m[2], v.Org)
	}
	return f, nil
}

// ptr records the name an address resolves back to.
func (c *collector) ptr(subject, ip string) {
	p := c.begin(methodDNSPTR, ip)
	names, err := net.LookupAddr(ip)
	if len(names) > 0 {
		var f facts
		f.add(subject, "ptr_record", strings.TrimSuffix(names[0], "."), names[0])
		p.Observations = f
	}
	p.end(err)
}

// ---- gateway: the router this computer talks to ----

func (c *collector) gateway(ip string) {
	if ip == "" {
		return
	}
	// Request its pages first, so it appears in the neighbor table.
	c.pages(subjectGateway, "http://"+ip+"/")

	obs := c.command(reading{parse: parseNeighbor, keep: true}, c.os.neighbor(ip)...)
	c.manufacturer(oui(find(obs, subjectGateway, "mac_address")))

	c.ptr(subjectGateway, ip)
	c.upnp(ip)
}

// parseNeighbor reads the first hardware address the neighbor table prints.
func parseNeighbor(text string) []Observation {
	var f facts
	for _, line := range lines(text) {
		if mac := macPattern.FindString(line); mac != "" {
			f.add(subjectGateway, "mac_address", mac, line)
			break
		}
	}
	return f
}

// oui returns the first three octets of a hardware address as AA:BB:CC, or
// "". They identify the manufacturer, not the device. macOS prints octets
// without leading zeros and Windows separates them with dashes.
func oui(mac string) string {
	octets := strings.FieldsFunc(mac, func(c rune) bool { return c == ':' || c == '-' })
	if len(octets) != 6 {
		return ""
	}
	for i, o := range octets[:3] {
		octets[i] = strings.ToUpper(fmt.Sprintf("%02s", o))
	}
	return strings.Join(octets[:3], ":")
}

// manufacturer looks up who a hardware address prefix is registered to.
func (c *collector) manufacturer(oui string) {
	if oui == "" {
		return
	}
	p := c.begin(methodHTTPGet, ouiEndpoint+oui)
	res, err := fetch(c.wan, ouiEndpoint+oui)
	switch {
	case err != nil:
	case !strings.HasPrefix(res.status, "200"):
		err = errors.New(res.status) // the server's own status line
	default:
		p.Observations = whole(subjectGateway, "oui_organization")(res.body)
	}
	p.end(err)
}

// upnp asks devices to announce themselves and reads the description the
// gateway publishes.
func (c *collector) upnp(gatewayIP string) {
	p := c.begin(methodSSDPSearch, ssdpAddress+" upnp:rootdevice")
	location, err := discoverUPnP(gatewayIP)
	p.end(err)
	if err != nil {
		return
	}

	p = c.begin(methodHTTPGet, location)
	res, err := fetch(c.lan, location)
	if err == nil {
		p.Observations, err = parseDescription(res.body)
	}
	p.end(err)
}

// discoverUPnP returns the address of the gateway's device description.
func discoverUPnP(gatewayIP string) (string, error) {
	group, err := net.ResolveUDPAddr("udp4", ssdpAddress)
	if err != nil {
		return "", err
	}
	conn, err := net.ListenUDP("udp4", nil)
	if err != nil {
		return "", err
	}
	defer conn.Close()
	if _, err := conn.WriteToUDP([]byte(ssdpSearch), group); err != nil {
		return "", err
	}
	if err := conn.SetReadDeadline(time.Now().Add(ssdpWait)); err != nil {
		return "", err
	}
	buf := make([]byte, 4096)
	for {
		n, from, err := conn.ReadFromUDP(buf)
		if err != nil {
			return "", err
		}
		if location := ssdpLocation(string(buf[:n])); from.IP.String() == gatewayIP && location != "" {
			return location, nil
		}
	}
}

// ssdpLocation returns the LOCATION header of a discovery answer, or "".
func ssdpLocation(answer string) string {
	for _, line := range strings.Split(answer, "\r\n") {
		if name, value, ok := strings.Cut(line, ":"); ok && strings.EqualFold(strings.TrimSpace(name), "location") {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

// parseDescription reads maker, model and serial from a UPnP device
// description. Raw is each element exactly as it appears.
func parseDescription(body string) ([]Observation, error) {
	var d struct {
		Device struct {
			Manufacturer string `xml:"manufacturer"`
			ModelName    string `xml:"modelName"`
			ModelNumber  string `xml:"modelNumber"`
			SerialNumber string `xml:"serialNumber"`
		} `xml:"device"`
	}
	if err := xml.Unmarshal([]byte(body), &d); err != nil {
		return nil, err
	}
	var f facts
	for _, field := range []struct{ attribute, element, value string }{
		{"manufacturer", "manufacturer", d.Device.Manufacturer},
		{"model_name", "modelName", d.Device.ModelName},
		{"model_number", "modelNumber", d.Device.ModelNumber},
		{"serial_number", "serialNumber", d.Device.SerialNumber},
	} {
		raw := regexp.MustCompile(`(?s)<` + field.element + `>.*?</` + field.element + `>`).FindString(body)
		f.add(subjectGateway, field.attribute, field.value, raw)
	}
	return f, nil
}

// ---- modem ----

func (c *collector) modem(gatewayIP string) {
	if strings.HasPrefix(gatewayIP, modemNetwork) {
		return // the home network uses the modem's address range
	}
	c.pages(subjectModem, modemURL)
}

// ---- device pages ----

// pages requests a device's front page and the pages it links to that look
// like they describe the device. It records the front page's status line
// and the first labelled maker, model and serial rows it finds. Pages are
// not stored: they can list other devices in the home and Wi-Fi settings.
//
// A page that arrived but whose response never ended is still read, and the
// probe records the error alongside what was read.
func (c *collector) pages(subject, front string) {
	queue := []string{front}
	queued := map[string]bool{front: true}
	seen := map[string]bool{} // attributes already recorded

	for i := 0; i < len(queue) && i < maxPages; i++ {
		p := c.begin(methodHTTPGet, queue[i])
		res, err := fetch(c.lan, queue[i])
		if res.answered() {
			var f facts
			if i == 0 {
				f.add(subject, "http_status", res.status, res.status)
			}
			p.Observations = append(f, unseen(deviceFields(subject, res.body), seen)...)
			for _, link := range pageLinks(res.url, res.body) {
				if !queued[link] {
					queued[link] = true
					queue = append(queue, link)
				}
			}
		}
		p.end(err)
	}
}

// deviceFields reads the labelled maker, model and serial rows of a page.
func deviceFields(subject, body string) []Observation {
	var f facts
	for _, m := range labelPattern.FindAllStringSubmatch(body, -1) {
		attribute := strings.Join(strings.Fields(strings.ToLower(m[1])), "_")
		if attribute == "model" {
			attribute = "model_name"
		}
		f.add(subject, attribute, m[2], m[0])
	}
	return f
}

// unseen returns the observations whose attribute is not yet in seen, and
// adds them to it.
func unseen(observations []Observation, seen map[string]bool) []Observation {
	var fresh []Observation
	for _, o := range observations {
		if !seen[o.Attribute] {
			seen[o.Attribute] = true
			fresh = append(fresh, o)
		}
	}
	return fresh
}

// pageLinks returns the pages worth following from a page: where it
// redirects to, and same-host links that look like device information.
func pageLinks(page *url.URL, body string) []string {
	var links []string
	if m := refreshPattern.FindStringSubmatch(body); m != nil {
		if target, err := page.Parse(m[1]); err == nil {
			links = append(links, target.String())
		}
	}
	for _, m := range hrefPattern.FindAllStringSubmatch(body, -1) {
		link, err := page.Parse(m[1])
		if err == nil && link.Host == page.Host && infoPagePattern.MatchString(link.Path) {
			links = append(links, link.String())
		}
	}
	return links
}
