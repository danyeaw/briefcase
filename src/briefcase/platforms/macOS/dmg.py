from briefcase.config import BaseConfig
from briefcase.exceptions import BriefcaseCommandError
from briefcase.platforms.macOS.app import (
    macOSAppBuildCommand,
    macOSAppCreateCommand,
    macOSAppMixin,
    macOSAppPublishCommand,
    macOSAppRunCommand,
    macOSAppUpdateCommand
)

try:
    import dmgbuild
except ImportError:
    # On non-macOS platforms, dmgbuild won't be installed.
    # Allow the plugin to be loaded; raise an error when tools are verified.
    dmgbuild = None


class macOSDmgMixin(macOSAppMixin):
    output_format = 'dmg'

    def distribution_path(self, app):
        return self.platform_path / '{app.formal_name}-{app.version}.dmg'.format(app=app)

    def verify_tools(self):
        super().verify_tools()
        if dmgbuild is None:
            raise BriefcaseCommandError("""
A macOS DMG can only be created on macOS.
""")


class macOSDmgCreateCommand(macOSDmgMixin, macOSAppCreateCommand):
    description = "Create and populate a macOS DMG."

    @property
    def app_template_url(self):
        "The URL for a cookiecutter repository to use when creating apps"
        return 'https://github.com/beeware/briefcase-{self.platform}-app-template.git'.format(
            self=self
        )


class macOSDmgUpdateCommand(macOSDmgMixin, macOSAppUpdateCommand):
    description = "Update an existing macOS DMG."


class macOSDmgBuildCommand(macOSDmgMixin, macOSAppBuildCommand):
    description = "Build a macOS DMG."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # External service APIs.
        # These are abstracted to enable testing without patching.
        self.dmgbuild = dmgbuild

    def build_app(self, app: BaseConfig, **kwargs):
        """
        Build a DMG application.

        :param app: The application to build
        """
        print()
        print("[{app.name}] Building DMG...".format(app=app))

        dmg_settings = {
            'files': [str(self.bundle_path(app))],
            'symlinks': {'Applications': '/Applications'},
            'icon_locations': {
                '{app.formal_name}.app'.format(app=app): (100, 100),
                'Applications': (300, 100),
            },
        }

        try:
            icon_filename = self.base_path / '{icon}.icns'.format(
                icon=app.installer_icon
            )
            if not icon_filename.exists():
                print("Can't find {filename}.icns for DMG installer icon".format(
                    filename=app.installer_icon
                ))
                raise AttributeError()
        except AttributeError:
            # No installer icon specified. Fall back to the app icon
            try:
                icon_filename = self.base_path / '{icon}.icns'.format(
                    icon=app.icon
                )
                if not icon_filename.exists():
                    print("Can't find {filename}.icns for fallback DMG installer icon".format(
                        filename=app.icon
                    ))
                    raise AttributeError()
            except AttributeError:
                icon_filename = None

        if icon_filename:
            dmg_settings['icon'] = icon_filename

        try:
            image_filename = self.base_path / '{image}.png'.format(
                image=app.installer_background
            )
            if image_filename.exists():
                dmg_settings['background'] = image_filename
            else:
                print("Can't find {filename}.png for DMG background".format(
                    filename=app.installer_background
                ))
        except AttributeError:
            # No installer background image provided
            pass

        self.dmgbuild.build_dmg(
            filename=self.distribution_path(app),
            volume_name='{app.formal_name} {app.version}'.format(app=app),
            settings=dmg_settings
        )


class macOSDmgRunCommand(macOSDmgMixin, macOSAppRunCommand):
    description = "Run a macOS DMG."


class macOSDmgPublishCommand(macOSDmgMixin, macOSAppPublishCommand):
    description = "Publish a macOS DMG."

    def add_options(self):
        self.parser.add_argument(
            '-c',
            '--channel',
            choices=['s3', 'github', 'appstore'],
            default='s3',
            metavar='channel',
            help='The channel to publish to'
        )


# Declare the briefcase command bindings
create = macOSDmgCreateCommand  # noqa
update = macOSDmgUpdateCommand  # noqa
build = macOSDmgBuildCommand  # noqa
run = macOSDmgRunCommand  # noqa
publish = macOSDmgPublishCommand  # noqa
