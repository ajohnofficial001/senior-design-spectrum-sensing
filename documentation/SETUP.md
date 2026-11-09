# Environment setup

## Current executable artifact

The preserved transmitter was generated with GNU Radio 3.10.12.0 and imports Python 3, PyQt5, GNU Radio Qt GUI and GNU Radio Soapy blocks. A compatible Soapy PlutoSDR driver, connected device and graphical session are required.

Install GNU Radio and hardware support through the platform's supported distribution/toolchain. Exact platform packages and a reproducible environment lock remain to be documented after testing on the team's laptops. No unverified pip requirements file is supplied for these system/hardware dependencies.

Check software imports without executing the transmitter:

```bash
python3 -c "from PyQt5 import Qt; from gnuradio import gr, qtgui, analog, blocks, soapy; print(gr.version())"
```

This checks imports only; it does not validate hardware or RF performance.

Open `gnuradio-companion transmitter/primary_tx.grc`. Review the PlutoSDR device argument `uri = usb:0.4.5`, center frequency, gain and sample rate for the local setup. Change the .grc source and regenerate its Python companion together.

Once the controlled RF setup is ready, running `python3 transmitter/primary_tx.py` starts transmission immediately. Stop through the GUI or Ctrl+C.

## Other subsystems

The imported simulation source and launch procedure are documented in [simulation](../simulation/README.md). It requires GNU Radio 3.10.12.0-compatible Python, filter/analog/blocks/Qt GUI modules, PyQt5 and sip with a graphical session; its active path needs no SDR hardware. Runtime reproduction remains pending. Receiver, cooperative and blockchain dependencies will be documented with their implementations. Record tested versions and device configuration in each experiment.
