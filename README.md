# Big Apple Connect Box

New York City launched
[Big Apple Connect](https://access.nyc.gov/programs/big-apple-connect/) to give
NYCHA residents "free, fast, reliable, and safe internet." This project checks
that promise from inside the home, where people actually use the connection,
and keeps the proof.

See it at [bigappleconnect.com](https://www.bigappleconnect.com).

> **This is an independent, personal project.** It is not affiliated with,
> endorsed by or run by the City of New York, NYCHA, or any internet provider.
> I'd welcome working with the city.

## What we're aiming for

1. **Measure what homes really get.** Day and night, not one speed test on a
   phone.
2. **Keep providers accountable.** Give households, advocates and the city
   evidence they can put next to what was promised.
3. **Help people get more from what they have.** Turn the results into plain
   advice for a home's own setup, like where the router sits.

## Where things stand

It's early. Here's what's real today and what isn't yet.

- **Works now:** a measuring program for Raspberry Pi, Linux, macOS and
  Windows. It runs on a computer you already have and saves every result.
- **Next:** the box itself: a small, low-cost computer, ready to plug into
  your router.
- **Later:** a website for a quick check with nothing to install, and a
  dashboard with an AI helper that suggests fixes based on your results.

## Quick start

On a Raspberry Pi, Linux or a Mac:

```sh
curl -L -o big-apple-connect-box https://github.com/malewis5/big-apple-connect-box/releases/latest/download/big-apple-connect-box_linux_arm64
chmod +x big-apple-connect-box
./big-apple-connect-box
```

That file is for a 64-bit Raspberry Pi. On another system, swap the end of the
address:

| System | File |
|---|---|
| Raspberry Pi (64-bit) | `big-apple-connect-box_linux_arm64` |
| Linux | `big-apple-connect-box_linux_amd64` |
| Mac with Apple silicon | `big-apple-connect-box_darwin_arm64` |
| Intel Mac | `big-apple-connect-box_darwin_amd64` |

On Windows, in PowerShell:

```powershell
curl.exe -L -o big-apple-connect-box.exe https://github.com/malewis5/big-apple-connect-box/releases/latest/download/big-apple-connect-box_windows_amd64.exe
.\big-apple-connect-box.exe
```

A scan takes about a minute. It prints what it found and saves it to
`evidence.db` in the current folder. Run it with `-daemon` to keep checking:
a quick check every 5 minutes and a full scan every hour.

The program isn't code-signed yet, so macOS and Windows may warn about it.
[Common problems](apps/box/README.md#common-problems) covers that, and
[Verify a download](apps/box/README.md#verify-a-download) shows how to check
that your copy is genuine.

## What it measures

- **Your setup:** cable or Wi-Fi, Wi-Fi signal, the router and modem, and the
  provider.
- **Your connection:** ping to the router, the provider and the wider
  internet; name lookup times; the route out; and a speed test.

It measures the same way as
[Netrics](https://github.com/internet-innovation/netrics), the software behind
the University of Chicago's home broadband study, so results from different
homes and cities can be compared.

## Your data

Results stay on your computer. Nothing is sent to this project.

A few outside services are used to take the measurements. The speed test runs
against [M-Lab](https://www.measurementlab.net), which publishes its test
records, including your public IP address.
[Outside services](apps/box/README.md#outside-services) lists every one and
what it receives.

`evidence.db` holds your public IP address and your equipment's serial
numbers, so be careful who you share it with.

## The repository

```
apps/box/      the measuring program, in Go
apps/web/      the website, in Next.js
design/box/    Blender scripts for the box's 3D model and the site's icons
```

For the full details (what each scan records, the database, how each
measurement works and how releases are made), see
[`apps/box/README.md`](apps/box/README.md).

To work on it, install [Go](https://go.dev), [Node.js](https://nodejs.org)
and [pnpm](https://pnpm.io), then:

```sh
pnpm install
pnpm build    # build both apps; the program lands in apps/box/bin
pnpm test     # run the tests
pnpm lint     # check both apps
pnpm dev      # run the website at http://localhost:3000
```

## Get involved

Questions, problems and corrections are welcome as
[issues](https://github.com/malewis5/big-apple-connect-box/issues).
[CONTRIBUTING.md](CONTRIBUTING.md) explains how to propose a change. Report
security problems privately, as [SECURITY.md](SECURITY.md) describes.

## License

[Apache-2.0](LICENSE). Use, copy, change and share it for any purpose, as long as
you keep the copyright and license notices and say what you changed.
