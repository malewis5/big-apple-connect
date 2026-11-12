package collector

import (
	"context"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// commandTimeout bounds any one command. The longest, a route trace on
// Windows, can take about a minute.
const commandTimeout = 2 * time.Minute

// recorder collects the probes of one scan. It is safe for concurrent use.
type recorder struct {
	mu   sync.Mutex
	list []*Probe
}

// begin starts a probe and records it.
func (r *recorder) begin(method, target string) *Probe {
	p := &Probe{Method: method, Target: target, StartedAt: time.Now().UTC()}
	r.mu.Lock()
	r.list = append(r.list, p)
	r.mu.Unlock()
	return p
}

// probes returns the probes recorded so far, in the order they began.
func (r *recorder) probes() []*Probe {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]*Probe(nil), r.list...)
}

// end records when the probe finished and the error returned, if any.
func (p *Probe) end(err error) {
	p.FinishedAt = time.Now().UTC()
	if err != nil {
		p.Err = err.Error()
	}
}

// A parser reads observations from text. It has no side effects.
type parser func(text string) []Observation

// A reading says how the text a probe returns is handled.
type reading struct {
	parse parser

	// keep stores the text when nothing could be read from it. It is set
	// only where the text holds nothing beyond what the collector may
	// store. Commands that also print this computer's hardware address or
	// the Wi-Fi network's name leave it unset.
	keep bool

	// during is the probe this one deliberately runs alongside.
	during *Probe
}

// command runs a program and records what the reading finds in its output.
func (r *recorder) command(rd reading, args ...string) []Observation {
	p := r.begin(methodExec, strings.Join(args, " "))
	ctx, cancel := context.WithTimeout(context.Background(), commandTimeout)
	defer cancel()
	out, err := exec.CommandContext(ctx, args[0], args[1:]...).CombinedOutput()
	return rd.finish(p, string(out), err)
}

// file reads a file and records what the reading finds in it.
func (r *recorder) file(rd reading, path string) []Observation {
	p := r.begin(methodFileRead, path)
	b, err := os.ReadFile(path)
	return rd.finish(p, string(b), err)
}

func (rd reading) finish(p *Probe, text string, err error) []Observation {
	p.ConcurrentWith = rd.during
	p.Observations = rd.parse(text)
	if len(p.Observations) == 0 && rd.keep {
		p.Output = text
	}
	p.end(err)
	return p.Observations
}

// facts builds a list of observations. A value that is empty once trimmed
// is not an observation.
type facts []Observation

func (f *facts) add(subject, attribute, value, raw string) {
	if value = strings.TrimSpace(value); value != "" {
		*f = append(*f, Observation{Subject: subject, Attribute: attribute, Value: value, Raw: raw})
	}
}

// find returns the first value observed for a subject's attribute, or "".
func find(observations []Observation, subject, attribute string) string {
	for _, o := range observations {
		if o.Subject == subject && o.Attribute == attribute {
			return o.Value
		}
	}
	return ""
}

func lines(text string) []string { return strings.Split(text, "\n") }

// labelled returns a parser for "label: value" lines. Each wanted label is
// recorded under the host attribute it maps to; every other line is
// dropped.
func labelled(wanted map[string]string) parser {
	return func(text string) []Observation {
		var f facts
		for _, line := range lines(text) {
			label, value, _ := strings.Cut(line, ":")
			if attribute, found := wanted[strings.TrimSpace(label)]; found {
				f.add(subjectHost, attribute, value, line)
			}
		}
		return f
	}
}

// whole returns a parser that records the entire text as one value.
func whole(subject, attribute string) parser {
	return func(text string) []Observation {
		var f facts
		f.add(subject, attribute, text, text)
		return f
	}
}
