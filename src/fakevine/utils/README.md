# FakeVine Utils

This is a set of utilities and scripts to support the use of FakeVine.

Run it using [uv](https://docs.astral.sh/uv/) with `uv run fakevine-utils --help` to see the command line arguments available.

## readme
Dump this README to the console.

## print-schema
Print the Simple CV DB schema to the console.  This schema is used for the Simple CV DB Trunk.

## convert-reddit-db
Converts a database dump of CV API responses that you might find somewhere, say reddit for arguments sake, into the Simple CV DB schema.  Don't make your tea based on the timers - they struggle with estimating from the stop/start of the commit batches, but they help with the memory footprint.  The latest version is pretty slow on a full dump, but it's better to be complete than fast and there's no reason to be using this tool regularly.