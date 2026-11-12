# Changelog

## 0.0.1 (2026-11-12)

The first release: one program that measures a home internet connection and saves what it finds to a local SQLite database.

* **The setup:** cable or Wi-Fi, link speed, Wi-Fi signal, the router and modem as they describe themselves, and the provider.
* **The measurements:** ping, last-mile delay, name-lookup time, hop count and an NDT7 speed test, following [Netrics](https://github.com/internet-innovation/netrics). The router is pinged during the speed test.
* **Two kinds of scan:** light every five minutes and full every hour, or one on demand.
* **Evidence as returned:** every stored value is kept with the exact text it was read from.
* **Downloads** for Raspberry Pi, Linux, Windows and macOS, each with a checksum and a build attestation.

Run on macOS and Linux. On Windows, the tests run.


### Features

* report the version the program was built from ([8b55519](https://github.com/malewis5/big-apple-connect-box/commit/8b555197343a79bf91e132b0fb439092aa40800d))
