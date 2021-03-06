#
# This file is part of LUNA.
#
# Copyright (c) 2020 Great Scott Gadgets <info@greatscottgadgets.com>
# SPDX-License-Identifier: BSD-3-Clause

""" Utilities for creating LUNA platforms. """

import logging

from nmigen import Signal, Record
from nmigen.build.res import ResourceError, Subsignal, Resource, Pins


class LUNAPlatform:
    """ Mixin that extends nMigen platforms with extra functionality."""

    def request_optional(self, name, number=0, *args, default, expected=False, **kwargs):
        """ Specialized version of .request() for "optional" I/O.

        If the platform has the a resource with the given name, it is requested
        and returned. Otherwise, this method returns the value provided in the default argument.

        This is useful for designs that support multiple platforms; and allows for
        resources such as e.g. LEDs to be omitted on platforms that lack them.

        Parameters
        ----------
        default: any
            The value that is returned in lieu of the relevant resources if the resource does not exist.
        expected: bool, optional
            If explicitly set to True, this function will emit a warning when the given pin is not present.
        """

        try:
            return self.request(name, number, *args, **kwargs)
        except ResourceError:
            log = logging.warnings if expected else logging.debug
            log(f"Skipping resource {name}/{number}, as it is not present on this platform.")
            return default
