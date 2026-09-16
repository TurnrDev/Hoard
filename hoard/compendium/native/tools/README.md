# RPGScript compiler tooling

Hoard vendors the Linux x86-64 `refresh_system_builder` supplied by version
1.3.0 of the official **RPGScript Language Support** VS Code extension:

- Marketplace: <https://marketplace.visualstudio.com/items?itemName=BlastervlaEnterprisesLLC.rpgscript>
- Native development documentation: <https://rpg-companion.app/dev>
- Publisher: Blastervla Enterprises LLC

The compiler and its development-tool schema are MIT licensed; the exact
notice shipped in the extension is retained in `LICENSE.md`. This licence is
separate from the licences covering system definitions and resource content.

Hoard automatically uses this binary on Linux x86-64. Other platforms can set
`RPG_COMPANION_COMPILER` to the `refresh_system_builder` bundled with their
installed extension. A configured compiler always takes precedence over the
vendored binary.

When updating the tool, record the extension version here, replace the binary
and schema from the same extension package, preserve its licence, and run the
native compilation tests before committing.
