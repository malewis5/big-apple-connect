# Contributing

Questions, problems, corrections and pull requests are welcome.

- **Something is wrong or unclear:** open an
  [issue](https://github.com/malewis5/big-apple-connect-box/issues).
- **A security problem:** report it privately. See [SECURITY.md](SECURITY.md).
- **A change:** open a pull request. For anything large, open an issue first
  so we can agree on the approach before you spend time on it.

## Set up

[Build from source](README.md#build-from-source) in the README lists what to
install and the commands to build, test and run both apps.

## Pull requests

- Changes reach `main` only through pull requests, and the maintainer
  merges them.
- The `ci` check has to pass. It runs the lint, tests and build for the
  apps your change touches. Run them yourself with `pnpm lint`, `pnpm test`
  and `pnpm build`.
- Pull requests are squashed into one commit, and the title becomes the
  commit message. Write it as a
  [Conventional Commit](https://www.conventionalcommits.org):
  `fix: ...` for a fix, `feat: ...` for a new capability, `docs: ...` for
  words only. Name the app when it helps: `fix(web): ...`. The changelog
  and version numbers are made from these titles.
- Write for a reader who is new to the project: plain words, in the code
  comments too.

## Privacy

The database (`*.db`) holds a home's public address and equipment serial
numbers. Don't attach it to an issue or commit it. Remove those details from
any output you paste.

## License

The project is [0BSD](LICENSE). By contributing, you agree that your
contribution is released under the same license.
