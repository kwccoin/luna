#
# This file is part of LUNA.
#
# Copyright (c) 2020 Great Scott Gadgets <info@greatscottgadgets.com>
# SPDX-License-Identifier: BSD-3-Clause

""" LogicBone Platform definitions.

This is a non-core platform. To use it, you'll need to set your LUNA_PLATFORM variable:

    > export LUNA_PLATFORM="luna.gateware.platform.logicbone:LogicbonePlatform"
or
    > export LUNA_PLATFORM="luna.gateware.platform.logicbone:Logicbone_85F_Platform"
"""

import os
import subprocess

from nmigen import *
from nmigen.build import *
from nmigen.vendor.lattice_ecp5 import *

from nmigen_boards.resources import *
from .core import LUNAPlatform


__all__ = ["LogicbonePlatform", "Logicbone_85F_Platform"]

class LogicboneDomainGenerator(Elaboratable):
    """ Simple clock domain generator for the Logicbone. """

    def __init__(self, *, clock_frequencies=None, clock_signal_name=None):
        pass

    def elaborate(self, platform):
        m = Module()
        locked = Signal()

        # Grab our default input clock.
        input_clock = platform.request(platform.default_clk, dir="i")

        # Create our domains; but don't do anything else for them, for now.
        m.domains.sync   = ClockDomain()
        m.domains.usb    = ClockDomain()
        m.domains.usb_io = ClockDomain()
        m.domains.fast   = ClockDomain()

        feedback = Signal()
        m.submodules.pll = Instance("EHXPLLL",

                # Status.
                o_LOCK=locked,

                # PLL parameters...
                p_PLLRST_ENA="DISABLED",
                p_INTFB_WAKE="DISABLED",
                p_STDBY_ENABLE="DISABLED",
                p_DPHASE_SOURCE="DISABLED",
                p_OUTDIVIDER_MUXA="DIVA",
                p_OUTDIVIDER_MUXB="DIVB",
                p_OUTDIVIDER_MUXC="DIVC",
                p_OUTDIVIDER_MUXD="DIVD",

                p_CLKI_DIV = 5,
                p_CLKOP_ENABLE = "ENABLED",
                p_CLKOP_DIV = 16,
                p_CLKOP_CPHASE = 9,
                p_CLKOP_FPHASE = 0,

                p_CLKOS_DIV = 10,
                p_CLKOS_CPHASE = 0,
                p_CLKOS_FPHASE = 0,


                p_CLKOS2_ENABLE = "ENABLED",
                p_CLKOS2_DIV = 10,
                p_CLKOS2_CPHASE = 0,
                p_CLKOS2_FPHASE = 0,

                p_CLKOS3_ENABLE = "ENABLED",
                p_CLKOS3_DIV = 40,
                p_CLKOS3_CPHASE = 5,
                p_CLKOS3_FPHASE = 0,

                p_FEEDBK_PATH = "CLKOP",
                p_CLKFB_DIV = 6,

                # Clock in.
                i_CLKI=input_clock,

                # Internal feedback.
                i_CLKFB=feedback,

                # Control signals.
                i_RST=0,
                i_PHASESEL0=0,
                i_PHASESEL1=0,
                i_PHASEDIR=1,
                i_PHASESTEP=1,
                i_PHASELOADREG=1,
                i_STDBY=0,
                i_PLLWAKESYNC=0,

                # Output Enables.
                i_ENCLKOP=0,
                i_ENCLKOS2=0,

                # Generated clock outputs.
                o_CLKOP=feedback,
                o_CLKOS2=ClockSignal("sync"),
                o_CLKOS3=ClockSignal("usb"),

                # Synthesis attributes.
                a_FREQUENCY_PIN_CLKI="25",
                a_FREQUENCY_PIN_CLKOP="48",
                a_FREQUENCY_PIN_CLKOS="48",
                a_FREQUENCY_PIN_CLKOS2="12",
                a_ICP_CURRENT="12",
                a_LPF_RESISTOR="8",
                a_MFG_ENABLE_FILTEROPAMP="1",
                a_MFG_GMCREF_SEL="2"
        )

        # We'll use our 48MHz clock for everything _except_ the usb domain...
        m.d.comb += [
            ClockSignal("usb_io")  .eq(ClockSignal("sync")),
            ClockSignal("fast")    .eq(ClockSignal("sync")),

            ResetSignal("sync")    .eq(~locked),
            ResetSignal("usb")     .eq(~locked),
            ResetSignal("usb_io")  .eq(~locked),
            ResetSignal("fast")    .eq(~locked),
        ]

        return m


class LogicbonePlatform(LatticeECP5Platform, LUNAPlatform):
    name        = "Logicbone"
    device      = "LFE5UM5G-45F"
    package     = "BG381"
    speed       = "8"

    default_clk = "refclk"
    default_rst = "rst"

    clock_domain_generator = LogicboneDomainGenerator
    default_usb_connection = "usb"

    resources   = [
        Resource("rst", 0, PinsN("C17", dir="i"), Attrs(IO_TYPE="LVCMOS33")),
        Resource("refclk", 0, Pins("M19", dir="i"), Attrs(IO_TYPE="LVCMOS18"), Clock(25e6)),

        # VBUS Detection is on the USB-C PD controller for both ports.
        DirectUSBResource("usb", 0, d_p="B12", d_n="C12", pullup="C16"),
        DirectUSBResource("usb", 1, d_p="R1",  d_n="T1",  pullup="T2"),

        *LEDResources(pins="D16 C15 C13 B13", attrs=Attrs(IO_TYPE="LVCMOS33")),

        *SwitchResources(pins={0: "U2"}, attrs=Attrs(IO_TYPE="LVCMOS33")),

        *SPIFlashResources(0,
            cs="R2", clk="U3", cipo="V2", copi="W2", wp="Y2", hold="W1",
            attrs=Attrs(IO_STANDARD="LVCMOS33")
        ),

        *SDCardResources(0,
            clk="E11", cmd="D15", cd="D14",
            dat0="D13", dat1="E13", dat2="E15", dat3="E13",
            attrs=Attrs(IO_STANDARD="LVCMOS33")
        ),

        Resource("eth_clk125",     0, Pins("A19", dir="i"),
                 Clock(125e6), Attrs(IO_TYPE="LVCMOS33")),
        Resource("eth_rgmii", 0,
            #Subsignal("rst",     PinsN("U17", dir="o")), ## Stolen for sys_reset usage on prototypes.
            Subsignal("int",     Pins("B20", dir="i")),
            Subsignal("mdc",     Pins("D12", dir="o")),
            Subsignal("mdio",    Pins("B19", dir="io")),
            Subsignal("tx_clk",  Pins("A15", dir="o")),
            Subsignal("tx_ctl",  Pins("B15", dir="o")),
            Subsignal("tx_data", Pins("A12 A13 C14 A14", dir="o")),
            Subsignal("rx_clk",  Pins("B18", dir="i")),
            Subsignal("rx_ctl",  Pins("A18", dir="i")),
            Subsignal("rx_data", Pins("B17 A17 B16 A16", dir="i")),
            Attrs(IO_TYPE="LVCMOS33")
        ),

        Resource("ddr3", 0,
            Subsignal("rst",     PinsN("P1", dir="o")),
            Subsignal("clk",     DiffPairs("M4", "N5", dir="o"), Attrs(IO_TYPE="LVDS")),
            Subsignal("clk_en",  Pins("K4", dir="o")),
            Subsignal("cs",      PinsN("M3", dir="o")),
            Subsignal("we",      PinsN("E4", dir="o")),
            Subsignal("ras",     PinsN("L1", dir="o")),
            Subsignal("cas",     PinsN("M1", dir="o")),
            Subsignal("a",       Pins("D5 F4 B3 F3 E5 C3 C4 A5 A3 B5 G3 F5 D2 A4 D3 E3", dir="o")),
            Subsignal("ba",      Pins("B4 H5 N2", dir="o")),
            Subsignal("dqs",     DiffPairs("K2 H4", "J1 G5", dir="io"), Attrs(IO_TYPE="LVDS")),
            Subsignal("dq",      Pins("G2 K1 F1 K3 H2 J3 G1 H1 B1 E1 A2 F2 C1 E2 C2 D1", dir="io")),
            Subsignal("dm",      Pins("L4 J5", dir="o")),
            Subsignal("odt",     Pins("C5", dir="o")),
            Attrs(IO_TYPE="SSTL135_I")
        )
    ]
    connectors = [
        Connector("P8", 0, """
        -   -   C20 D19 D20 E19 E20 F19 F20 G20 -   -   -   -   -   -
        -   -   -   -   -   -   G19 H20 J20 K20 C18 D17 D18 E17 E18 F18
        F17 G18 E16 F16 G16 H16 J17 J16 H18 H17 J19 K19 J18 K18
        """),
        Connector("P9", 0, """
        -   -   -   -   -   -   -   -   -   -   -   A11 B11 A10 C10 A9
        B9  C11 A8  -   -   D9  C8  B8  A7  A6  B6  D8  C7  D7  C6  D6
        -   -   -   -   -   -   -   -   -   B10 E10 -   -   -
        """),
    ]


    def toolchain_prepare(self, fragment, name, **kwargs):
        overrides = dict(ecppack_opts="--compress --spimode qspi --freq 38.8")
        overrides.update(kwargs)
        return super().toolchain_prepare(fragment, name, **overrides, **kwargs)

    def toolchain_program(self, products, name):
        dfu_util = os.environ.get("DFU_UTIL", "dfu-util")
        with products.extract("{}.bit".format(name)) as bitstream_filename:
            subprocess.check_call([dfu_util, "-d", "1d50:615d", "-a", "0", "-R", "-D", bitstream_filename])



class Logicbone_85F_Platform(LogicbonePlatform):
    name        = "Logicbone (85F Variant)"
    device      = "LFE5UM5G-85F"
