import enum
import json
import subprocess

from briefcase.exceptions import BriefcaseCommandError


class DeviceState(enum.Enum):
    SHUTDOWN = 0
    BOOTED = 1
    SHUTTING_DOWN = 10
    UNKNOWN = 99


def ensure_xcode_is_installed(min_version=None, sub=subprocess):
    """
    Determine if an appropriate version of Xcode is installed.

    Raises an exception if Xcode is not installed, or if the version that is
    installed doesn't meet the minimum requirement.

    :param min_version: The minimum allowed version of Xcode, specified as a
        tuple of integers (e.g., (11, 2, 1)). Default: ``None``, meaning there
        is no minimum version.
    :param sub: the module for starting subprocesses. Defaults to
        Python's builtin; used for testing purposes.
    """

    try:
        output = sub.check_output(
            ['xcodebuild', '-version'],
            universal_newlines=True
        )

        if min_version is not None:
            if output.startswith('Xcode '):
                try:
                    # Split content up to the first \n
                    # then split the content after the first space
                    # and split that content on the dots.
                    # Append 0's to fill any gaps caused by
                    # version numbers that don't have a minor version.
                    version = tuple(
                        int(v)
                        for v in output.split('\n')[0].split(' ')[1].split('.')
                    ) + (0, 0)

                    if version < min_version:
                        raise BriefcaseCommandError(
                            "Xcode {min_version} is required; {version} is installed. Please update Xcode.".format(
                                min_version='.'.join(str(v) for v in min_version),
                                version='.'.join(str(v) for v in version),
                            )
                        )
                    return
                except IndexError:
                    pass

            print("""
*************************************************************************
** WARNING: Unable to determine the version of Xcode that is installed **
*************************************************************************

   Briefcase will proceed assume everything is OK, but if you
   experience problems, this is almost certainly the cause of those
   problems.

   Please report this as a bug at:

     https://github.com/beeware/briefcase/issues/

   In your report, please including the output from running:

     xcodebuild -version

   from the command prompt.

*************************************************************************

""")

    except subprocess.CalledProcessError:
        raise BriefcaseCommandError("""
Xcode is not installed.

You can install Xcode from the macOS App Store.
""")


def get_simulators(os_name, sub=subprocess):
    """
    Obtain the simulators available on this machine.

    The return value is a 2 level dictionary. The outer dictionary is
    keyed by OS version; the inner dictionary for each OS version
    contains the details of the available simulators, keyed by UDID.

    :param os_name: The OS that we want to simulate.
        One of `"iOS"`, `"watchOS"`, or `"tvOS"`.
    :param sub: the module for starting subprocesses. Defaults to
        Python's builtin; used for testing purposes.
    :returns: A dictionary of available simulators.
    """
    try:
        simctl_data = json.loads(
            sub.check_output(
                ['xcrun', 'simctl', 'list', '-j'],
                universal_newlines=True
            )
        )

        os_versions = {
            runtime['name'].split(' ', 1)[1]: runtime['identifier']
            for runtime in simctl_data['runtimes']
            if runtime['name'].startswith('{os_name} '.format(os_name=os_name))
            and runtime['isAvailable']
        }

        simulators = {
            version: {
                device['udid']: device['name']
                for device in simctl_data['devices'][identifier]
                if device['isAvailable']
            }
            for version, identifier in os_versions.items()
        }

        return simulators

    except subprocess.CalledProcessError:
        raise BriefcaseCommandError(
            "Unable to run xcrun simctl."
        )


def get_device_state(udid, sub=subprocess):
    """
    Determine the state of an iOS simulator device.

    :param udid: The UDID of the device to inspect
    :param sub: the module for starting subprocesses. Defaults to
        Python's builtin; used for testing purposes.
    :returns: The status of the device, as a DeviceState enum.
    """
    try:
        simctl_data = json.loads(
            sub.check_output(
                ['xcrun', 'simctl', 'list', 'devices', '-j', udid],
                universal_newlines=True
            )
        )

        for runtime, devices in simctl_data['devices'].items():
            for device in devices:
                if device['udid'] == udid:
                    return {
                        'Booted': DeviceState.BOOTED,
                        'Shutting Down': DeviceState.SHUTTING_DOWN,
                        'Shutdown': DeviceState.SHUTDOWN,
                    }.get(device['state'], DeviceState.UNKNOWN)

        # If we fall out the bottom of the loop, the UDID didn't match
        # so we raise an error.
        raise BriefcaseCommandError(
            "Unable to determine status of device {udid}.".format(
                udid=udid
            )
        )
    except subprocess.CalledProcessError:
        raise BriefcaseCommandError(
            "Unable to run xcrun simctl."
        )
