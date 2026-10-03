# Black Box

Black Box is a flight recorder for AI agents. It localizes failed execution steps, verifies blame through counterfactual replay, and repairs only affected work.

## Bootstrap

```sh
make install
make test
make lint
```

Run the frontend with `make web` and inspect the CLI with `bb --help`.
