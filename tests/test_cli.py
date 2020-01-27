import contextlib
import inspect
import os
import shutil
import unittest

from click.testing import CliRunner
from mock import MagicMock

from cli.internal.utils.remote import ApiError
from cli.internal.utils.store import Store
from cli.mason import Config
from cli.mason import cli
from cli.version import __version__
from tests import __tests_root__


class CliTest(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

        os.environ['_MASON_CLI_TEST_MODE'] = 'TRUE'

    def test__version__command_prints_info(self):
        result = self.runner.invoke(cli, ['version'])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            Mason CLI v{}
            Copyright (C) 2019 Mason America (https://bymason.com)
            License Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0>
        """.format(__version__)))

    def test__version__V_flag_prints_info(self):
        result = self.runner.invoke(cli, ['-V'])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            Mason CLI v{}
            Copyright (C) 2019 Mason America (https://bymason.com)
            License Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0>
        """.format(__version__)))

    def test__version__version_option_prints_info(self):
        result = self.runner.invoke(cli, ['--version'])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            Mason CLI v{}
            Copyright (C) 2019 Mason America (https://bymason.com)
            License Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0>
        """.format(__version__)))

    def test__logging__starts_at_info_level_by_default(self):
        result = self.runner.invoke(cli, ['version'])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn('Lowest logging level activated.', result.output)
        self.assertNotIn('debug: Debug logging activated.', result.output)

    def test__logging__switching_to_debug_level_logs_debug_messages(self):
        result = self.runner.invoke(cli, ['-v', 'debug', 'version'])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn('Lowest logging level activated.', result.output)
        self.assertIn('debug: Debug logging activated.', result.output)

    def test__logging__switching_to_custom_level_logs_custom_messages(self):
        result = self.runner.invoke(cli, ['-v', '1', 'version'])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Lowest logging level activated.', result.output)
        self.assertIn('debug: Debug logging activated.', result.output)

    def test__logging__switching_to_debug_level_through_env_var_logs_debug_messages(self):
        os.environ['LOGLEVEL'] = 'DEBUG'
        result = self.runner.invoke(cli, ['version'])
        del os.environ['LOGLEVEL']

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn('Lowest logging level activated.', result.output)
        self.assertIn('debug: Debug logging activated.', result.output)

    def test__logging__switching_to_custom_level_through_env_var_logs_custom_messages(self):
        os.environ['LOGLEVEL'] = '1'
        result = self.runner.invoke(cli, ['version'])
        del os.environ['LOGLEVEL']

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Lowest logging level activated.', result.output)
        self.assertIn('debug: Debug logging activated.', result.output)

    def test__logging__colors_are_enabled_by_default(self):
        result = self.runner.invoke(cli, ['-v', 'debug', 'version'], color=True)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertIn(b'\x1b[34mdebug: \x1b[0mDebug logging activated.', result.stdout_bytes)

    def test__logging__colors_can_be_disabled(self):
        result = self.runner.invoke(cli, ['-v', 'debug', '--no-color', 'version'], color=True)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertNotIn(b'\x1b[34mdebug: \x1b[0mDebug logging activated.', result.stdout_bytes)

    def test__cli__default_creds_are_retrieved_from_disk(self):
        with self.runner.isolated_filesystem():
            auth_store = Store('fake-auth', {}, os.path.abspath(''), False)
            auth_store['api_key'] = 'Foobar'
        config = Config(auth_store=auth_store)

        result = self.runner.invoke(cli, ['version'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

        self.assertDictEqual(auth_store._fields, {'api_key': 'Foobar'})

    def test__cli__api_key_option_updates_creds(self):
        with self.runner.isolated_filesystem():
            auth_store = Store('fake-auth', {}, os.path.abspath(''), False)
            auth_store['api_key'] = 'Foobar'
        config = Config(auth_store=auth_store)

        result = self.runner.invoke(cli, ['--token', 'New foobar', 'version'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

        self.assertDictEqual(auth_store._fields, {'api_key': 'New foobar'})
        auth_store.clear()
        auth_store.restore()
        self.assertDictEqual(auth_store._fields, {})

    def test__init__outside_home_dir_shows_warning(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        with self.runner.isolated_filesystem():
            current_dir = os.path.abspath('.')
            result = self.runner.invoke(cli, ['init'], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""

                    ##     ##    ###     ######   #######  ##    ##
                    ###   ###   ## ##   ##    ## ##     ## ###   ##
                    #### ####  ##   ##  ##       ##     ## ####  ##
                    ## ### ## ##     ##  ######  ##     ## ## ## ##
                    ##     ## #########       ## ##     ## ##  ####
                    ##     ## ##     ## ##    ## ##     ## ##   ###
                    ##     ## ##     ##  ######   #######  ##    ##

            You're about to initialize a Mason project in this directory:

              {}

            warning: You are currently outside your home directory.
            Are you ready to proceed? [Y/n]: n
            Aborted!
        """.format(current_dir)))

    def test__init__in_home_dir_shows_warning(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        with self._cd(os.path.expanduser('~')):
            current_dir = os.path.abspath('.')
            result = self.runner.invoke(cli, ['init'], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""

                    ##     ##    ###     ######   #######  ##    ##
                    ###   ###   ## ##   ##    ## ##     ## ###   ##
                    #### ####  ##   ##  ##       ##     ## ####  ##
                    ## ### ## ##     ##  ######  ##     ## ## ## ##
                    ##     ## #########       ## ##     ## ##  ####
                    ##     ## ##     ## ##    ## ##     ## ##   ###
                    ##     ## ##     ##  ######   #######  ##    ##

            You're about to initialize a Mason project in this directory:

              {}

            warning: You are initializing your home directory as a Mason project.
            Are you ready to proceed? [Y/n]: n
            Aborted!
        """.format(current_dir)))

    def test__init__in_existing_mason_project_dir_shows_warning(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        with self._home_dir_isolated_filesystem():
            current_dir = os.path.abspath('.')
            open(os.path.join(current_dir, '.masonrc'), "w").close()

            result = self.runner.invoke(cli, ['init'], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""

                    ##     ##    ###     ######   #######  ##    ##
                    ###   ###   ## ##   ##    ## ##     ## ###   ##
                    #### ####  ##   ##  ##       ##     ## ####  ##
                    ## ### ## ##     ##  ######  ##     ## ## ## ##
                    ##     ## #########       ## ##     ## ##  ####
                    ##     ## ##     ## ##    ## ##     ## ##   ###
                    ##     ## ##     ##  ######   #######  ##    ##

            You're about to initialize a Mason project in this directory:

              {}

            warning: You are initializing in an existing Mason project directory.
            Are you ready to proceed? [Y/n]: n
            Aborted!
        """.format(current_dir)))

    def test__init__selecting_new_project_succeeds(self):
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value=None)
        interactivity = MagicMock()
        interactivity.pick = MagicMock(return_value=('project-id', 0))
        config = Config(
            auth_store=self._initialized_auth_store(),
            api=api,
            interactivity=interactivity
        )

        with self._home_dir_isolated_filesystem():
            current_dir = os.path.abspath('.')

            result = self.runner.invoke(cli, ['init'], obj=config, input='y\nproject-id')

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""

                    ##     ##    ###     ######   #######  ##    ##
                    ###   ###   ## ##   ##    ## ##     ## ###   ##
                    #### ####  ##   ##  ##       ##     ## ####  ##
                    ## ### ## ##     ##  ######  ##     ## ## ## ##
                    ##     ## #########       ## ##     ## ##  ####
                    ##     ## ##     ## ##    ## ##     ## ##   ###
                    ##     ## ##     ##  ######   #######  ##    ##

            You're about to initialize a Mason project in this directory:

              {}

            Are you ready to proceed? [Y/n]: y
            Enter your new project ID: project-id

            Where should Mason look for apps? (Enter multiple paths separated by a comma, or leave blank if none.): 

            Writing configuration file to mason.yml...
            Writing project information to .masonrc...

            Mason initialization complete!
        """.format(current_dir)))

    def test__init__selecting_existing_project_succeeds(self):
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value=None)
        interactivity = MagicMock()
        interactivity.pick = MagicMock(return_value=('project-id', 1))
        config = Config(
            auth_store=self._initialized_auth_store(),
            api=api,
            interactivity=interactivity
        )

        with self._home_dir_isolated_filesystem():
            current_dir = os.path.abspath('.')

            result = self.runner.invoke(cli, ['init'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""

                    ##     ##    ###     ######   #######  ##    ##
                    ###   ###   ## ##   ##    ## ##     ## ###   ##
                    #### ####  ##   ##  ##       ##     ## ####  ##
                    ## ### ## ##     ##  ######  ##     ## ## ## ##
                    ##     ## #########       ## ##     ## ##  ####
                    ##     ## ##     ## ##    ## ##     ## ##   ###
                    ##     ## ##     ##  ######   #######  ##    ##

            You're about to initialize a Mason project in this directory:

              {}

            Are you ready to proceed? [Y/n]: 

            Where should Mason look for apps? (Enter multiple paths separated by a comma, or leave blank if none.): 

            Writing configuration file to mason.yml...
            Writing project information to .masonrc...

            Mason initialization complete!
        """.format(current_dir)))

    def test__init__selecting_apps_succeeds(self):
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value=None)
        interactivity = MagicMock()
        interactivity.pick = MagicMock(return_value=('project-id', 1))
        config = Config(
            auth_store=self._initialized_auth_store(),
            api=api,
            interactivity=interactivity
        )

        with self._home_dir_isolated_filesystem():
            current_dir = os.path.abspath('.')
            os.makedirs(os.path.join(current_dir, 'apps'))
            os.makedirs(os.path.join(current_dir, 'apps2'))

            apk_file = os.path.join(__tests_root__, 'res/v1.apk')
            shutil.copyfile(apk_file, os.path.join(current_dir, 'apps/app.apk'))

            result = self.runner.invoke(cli, ['init'], obj=config, input='y\nfake-dir\napps, apps2')

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""

                    ##     ##    ###     ######   #######  ##    ##
                    ###   ###   ## ##   ##    ## ##     ## ###   ##
                    #### ####  ##   ##  ##       ##     ## ####  ##
                    ## ### ## ##     ##  ######  ##     ## ## ## ##
                    ##     ## #########       ## ##     ## ##  ####
                    ##     ## ##     ## ##    ## ##     ## ##   ###
                    ##     ## ##     ##  ######   #######  ##    ##

            You're about to initialize a Mason project in this directory:

              {}

            Are you ready to proceed? [Y/n]: y

            App directories found: apps
            Where should Mason look for apps? (Enter multiple paths separated by a comma, or leave blank if none.): fake-dir
            error: Path does not exist: {}
            Where should Mason look for apps? (Enter multiple paths separated by a comma, or leave blank if none.): apps, apps2

            Writing configuration file to mason.yml...
            Writing project information to .masonrc...

            Mason initialization complete!
        """.format(current_dir, os.path.join(current_dir, 'fake-dir'))))

    def test__register_config__no_files_fails(self):
        result = self.runner.invoke(cli, ['register', 'config'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__register_config__non_existent_file_fails(self):
        result = self.runner.invoke(cli, ['register', 'config', 'foobar'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__register_config__no_creds_fails(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'config', config_file], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__register_config__existing_artifact_fails(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        api = MagicMock()
        api.upload_artifact = MagicMock(side_effect=ApiError(
            'Artifact already exists and cannot be overwritten'))
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'config', config_file], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            --------- OS Config ---------
            File Name: {}
            File size: 184
            Name: project-id
            Version: 1
            -----------------------------
            Continue register? [Y/n]: 
            error: Artifact already exists and cannot be overwritten
            Aborted!
        """.format(config_file)))

    def test__register_config__latest_non_existent_apk_fails(self):
        config_file = os.path.join(__tests_root__, 'res/complex-project/config3.yml')
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value=None)
        config = Config(
            auth_store=self._initialized_auth_store(),
            endpoints_store=self._initialized_endpoints_store(),
            api=api
        )

        result = self.runner.invoke(cli, ['register', 'config', config_file], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Apk 'com.example.app2' not found, register it first.
            Aborted!
        """))

    def test__register_config__negative_confirmation_aborts(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'config', config_file], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            --------- OS Config ---------
            File Name: {}
            File size: 184
            Name: project-id
            Version: 1
            -----------------------------
            Continue register? [Y/n]: n
            Aborted!
        """.format(config_file)))

    def test__register_config__file_is_registered(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'config', config_file], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            --------- OS Config ---------
            File Name: {}
            File size: 184
            Name: project-id
            Version: 1
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id' registered.
        """.format(config_file)))

    def test__register_config__rewritten_file_is_registered(self):
        config_file = os.path.join(__tests_root__, 'res/config4.yml')
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value={'version': '41'})
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'config', config_file], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            --------- OS Config ---------
            File Name: {}
            File size: 262
            Name: project-id4
            Version: 42
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id4' registered.
        """.format(config_file)))

    def test__register_config__files_are_registered(self):
        config_file1 = os.path.join(__tests_root__, 'res/config.yml')
        config_file2 = os.path.join(__tests_root__, 'res/config2.yml')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'register', 'config', config_file1, config_file2
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            --------- OS Config ---------
            File Name: {}
            File size: 184
            Name: project-id
            Version: 1
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id' registered.

            --------- OS Config ---------
            File Name: {}
            File size: 171
            Name: project-id2
            Version: 2
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id2' registered.
        """.format(config_file1, config_file2)))

    def test__register_apk__no_files_fails(self):
        result = self.runner.invoke(cli, ['register', 'apk'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__register_apk__non_existent_file_fails(self):
        result = self.runner.invoke(cli, ['register', 'apk', 'foobar'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__register_apk__no_creds_fails(self):
        apk_file = os.path.join(__tests_root__, 'res/v1.apk')
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'apk', apk_file], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__register_apk__existing_artifact_fails(self):
        apk_file = os.path.join(__tests_root__, 'res/v1.apk')
        api = MagicMock()
        api.upload_artifact = MagicMock(side_effect=ApiError(
            'Artifact already exists and cannot be overwritten'))
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'apk', apk_file], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            error: Artifact already exists and cannot be overwritten
            Aborted!
        """.format(apk_file)))

    def test__register_apk__negative_confirmation_aborts(self):
        apk_file = os.path.join(__tests_root__, 'res/v1.apk')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'apk', apk_file], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: n
            Aborted!
        """.format(apk_file)))

    def test__register_apk__file_is_registered(self):
        apk_file = os.path.join(__tests_root__, 'res/v1.apk')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'apk', apk_file], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' registered.
        """.format(apk_file)))

    def test__register_apk__files_are_registered(self):
        apk_file1 = os.path.join(__tests_root__, 'res/v1.apk')
        apk_file2 = os.path.join(__tests_root__, 'res/v1and2.apk')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'apk', apk_file1, apk_file2], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' registered.

            ------------ APK ------------
            File Name: {}
            File size: 1323413
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' registered.
        """.format(apk_file1, apk_file2)))

    def test__register_media__no_files_fails(self):
        result = self.runner.invoke(cli, ['register', 'media', 'bootanimation', 'Anim name', '1'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__register_media__non_existent_file_fails(self):
        result = self.runner.invoke(
            cli, ['register', 'media', 'bootanimation', 'Anim name', '1', 'foobar'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__register_media__invalid_version_fails(self):
        media_file = os.path.join(__tests_root__, 'res/bootanimation.zip')
        result = self.runner.invoke(
            cli, ['register', 'media', 'bootanimation', 'Anim name', 'invalid', media_file])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__register_media__no_creds_fails(self):
        media_file = os.path.join(__tests_root__, 'res/bootanimation.zip')
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'register', 'media',
            'bootanimation', 'Anim name', '1', media_file
        ], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__register_media__negative_confirmation_aborts(self):
        media_file = os.path.join(__tests_root__, 'res/bootanimation.zip')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'register', 'media',
            'bootanimation', 'Anim name', '1', media_file
        ], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ----------- MEDIA -----------
            File Name: {}
            File size: 3156136
            Name: Anim name
            Version: 1
            Type: bootanimation
            -----------------------------
            Continue register? [Y/n]: n
            Aborted!
        """.format(media_file)))

    def test__register_media__file_is_registered(self):
        media_file = os.path.join(__tests_root__, 'res/bootanimation.zip')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'register', 'media',
            'bootanimation', 'Anim name', '1', media_file
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ----------- MEDIA -----------
            File Name: {}
            File size: 3156136
            Name: Anim name
            Version: 1
            Type: bootanimation
            -----------------------------
            Continue register? [Y/n]: 
            Media 'Anim name' registered.
        """.format(media_file)))

    def test__register_media__latest_file_is_registered(self):
        media_file = os.path.join(__tests_root__, 'res/bootanimation.zip')
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value={'version': '41'})
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'register', 'media',
            'bootanimation', 'Anim name', 'latest', media_file
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ----------- MEDIA -----------
            File Name: {}
            File size: 3156136
            Name: Anim name
            Version: 42
            Type: bootanimation
            -----------------------------
            Continue register? [Y/n]: 
            Media 'Anim name' registered.
        """.format(media_file)))

    def test__register_project__no_context_fails(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['register', 'project'], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: .masonrc file not found. Please run 'mason init' to create the project context.
            Aborted!
        """))

    def test__register_project__non_existent_resource_fails(self):
        invalid_project = os.path.join(__tests_root__, 'res/invalid-project')
        config_file = os.path.join(__tests_root__, 'res/invalid-project/mason.yml')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        with self._cd(invalid_project):
            result = self.runner.invoke(cli, ['register', 'project'], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Project resource does not exist: {}
            Aborted!
        """.format(config_file)))

    def test__register_project__no_creds_fails(self):
        simple_project = os.path.join(__tests_root__, 'res/simple-project')
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        with self._cd(simple_project):
            result = self.runner.invoke(cli, ['register', 'project'], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__register_project__negative_confirmation_aborts(self):
        simple_project = os.path.join(__tests_root__, 'res/simple-project')
        apk_file = os.path.join(__tests_root__, 'res/simple-project/v1.apk')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        with self._cd(simple_project):
            result = self.runner.invoke(cli, ['register', 'project'], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: n
            Aborted!
        """.format(apk_file)))

    def test__register_project__app_not_present_fails(self):
        no_app_project = os.path.join(__tests_root__, 'res/no-app-project')
        apk_file = os.path.join(__tests_root__, 'res/no-app-project/v1.apk')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        with self._cd(no_app_project):
            result = self.runner.invoke(cli, ['register', 'project'], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' registered.
            error: App '{}' declared in project context not found in project configuration.
            Aborted!
        """.format(apk_file, 'com.example.unittestapp1')))

    def test__register_project__config_already_present_failed(self):
        simple_project = os.path.join(__tests_root__, 'res/simple-project')
        config_file = os.path.join(__tests_root__, 'res/simple-project/mason.yml')
        apk_file = os.path.join(__tests_root__, 'res/simple-project/v1.apk')
        api = MagicMock()
        api.upload_artifact = MagicMock(side_effect=ApiError(
            'Artifact already exists and cannot be overwritten'))
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        with self._cd(simple_project):
            result = self.runner.invoke(cli, ['register', 'project'], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' already registered, ignoring.

            --------- OS Config ---------
            File Name: {}
            File size: 189
            Name: project-id2
            Version: 2
            -----------------------------
            Continue register? [Y/n]: 
            error: Artifact already exists and cannot be overwritten
            Aborted!
        """.format(apk_file, config_file)))

    def test__register_project__artifact_already_present_is_ignored(self):
        # noinspection PyUnusedLocal
        def api_response(binary, artifact):
            if artifact.get_type() == 'apk':
                raise ApiError('Artifact already exists and cannot be overwritten')

        simple_project = os.path.join(__tests_root__, 'res/simple-project')
        config_file = os.path.join(__tests_root__, 'res/simple-project/mason.yml')
        apk_file = os.path.join(__tests_root__, 'res/simple-project/v1.apk')
        api = MagicMock()
        api.upload_artifact = MagicMock(side_effect=api_response)
        api.get_build = MagicMock(return_value={'data': {'status': 'COMPLETED'}})
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        with self._cd(simple_project):
            result = self.runner.invoke(cli, ['register', 'project'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' already registered, ignoring.

            --------- OS Config ---------
            File Name: {}
            File size: 189
            Name: project-id2
            Version: 2
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id2' registered.

            Build queued.
            You can see the status of your build at
            https://platform.bymason.com/controller/projects/project-id2

            Build completed.
        """.format(apk_file, config_file)))

    def test__register_project__simple_project_is_registered_and_built(self):
        simple_project = os.path.join(__tests_root__, 'res/simple-project')
        config_file = os.path.join(__tests_root__, 'res/simple-project/mason.yml')
        apk_file = os.path.join(__tests_root__, 'res/simple-project/v1.apk')
        api = MagicMock()
        api.get_build = MagicMock(return_value={'data': {'status': 'COMPLETED'}})
        config = Config(
            auth_store=self._initialized_auth_store(),
            endpoints_store=self._initialized_endpoints_store(),
            api=api
        )

        with self._cd(simple_project):
            result = self.runner.invoke(cli, ['register', 'project'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' registered.

            --------- OS Config ---------
            File Name: {}
            File size: 189
            Name: project-id2
            Version: 2
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id2' registered.

            Build queued.
            You can see the status of your build at
            https://platform.bymason.com/controller/projects/project-id2

            Build completed.
        """.format(apk_file, config_file)))

    def test__register_project__complex_project_is_registered_and_built(self):
        complex_project = os.path.join(__tests_root__, 'res/complex-project')
        config_file1 = os.path.join(__tests_root__, 'res/complex-project/.mason/config2.yml')
        config_file2 = os.path.join(__tests_root__, 'res/complex-project/config3.yml')
        apk_file1 = os.path.join(__tests_root__, 'res/complex-project/test-path/v1.apk')
        apk_file2 = os.path.join(__tests_root__, 'res/complex-project/built-apks/built.apk')
        boot_animation1 = os.path.join(
            __tests_root__, 'res/complex-project/anims/bootanimation.zip')
        boot_animation2 = os.path.join(
            __tests_root__, 'res/complex-project/anims/bootanimation2.zip')
        api = MagicMock()
        api.get_build = MagicMock(return_value={'data': {'status': 'COMPLETED'}})
        api.get_latest_artifact = MagicMock(return_value={
            'version': '41',
            'checksum': {'sha1': 'e7788dca3a3797fd152825e600047e7cef870d98'}
        })
        config = Config(
            auth_store=self._initialized_auth_store(),
            endpoints_store=self._initialized_endpoints_store(),
            api=api
        )

        with self._cd(complex_project):
            result = self.runner.invoke(cli, ['register', 'project'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ------------ APK ------------
            File Name: {}
            File size: 1319297
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' registered.

            ------------ APK ------------
            File Name: {}
            File size: 1323413
            Package: com.example.unittestapp1
            Version Name: 1.0
            Version Code: 1
            -----------------------------
            Continue register? [Y/n]: 
            Apk 'com.example.unittestapp1' registered.

            ----------- MEDIA -----------
            File Name: {}
            File size: 3156136
            Name: anim-1
            Version: 41
            Type: bootanimation
            -----------------------------
            Continue register? [Y/n]: 
            Media 'anim-1' registered.
            
            ----------- MEDIA -----------
            File Name: {}
            File size: 166
            Name: anim-2
            Version: 42
            Type: bootanimation
            -----------------------------
            Continue register? [Y/n]: 
            Media 'anim-2' registered.

            --------- OS Config ---------
            File Name: {}
            File size: 189
            Name: project-id2
            Version: 2
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id2' registered.

            Build queued.
            You can see the status of your build at
            https://platform.bymason.com/controller/projects/project-id2

            Build completed.

            --------- OS Config ---------
            File Name: {}
            File size: 396
            Name: project-id3
            Version: 42
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id3' registered.

            Build queued.
            You can see the status of your build at
            https://platform.bymason.com/controller/projects/project-id3

            Build completed.
        """.format(apk_file1, apk_file2,
                   boot_animation1, boot_animation2,
                   config_file1, config_file2)))

    def test__build__invalid_version_fails(self):
        result = self.runner.invoke(cli, ['build', 'project-id', 'invalid'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__build__no_creds_fails(self):
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['build', 'project-id', '1'], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__build__build_is_started(self):
        api = MagicMock()
        config = Config(
            auth_store=self._initialized_auth_store(),
            endpoints_store=self._initialized_endpoints_store(),
            api=api
        )

        result = self.runner.invoke(cli, ['build', 'project-id', '1'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            Build queued.
            You can see the status of your build at
            https://platform.bymason.com/controller/projects/project-id
        """))

    def test__build__build_is_started_and_awaited_for_completion(self):
        api = MagicMock()
        api.get_build = MagicMock(return_value={'data': {'status': 'COMPLETED'}})
        config = Config(
            auth_store=self._initialized_auth_store(),
            endpoints_store=self._initialized_endpoints_store(),
            api=api
        )

        result = self.runner.invoke(cli, ['build', '--await', 'project-id', '1'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            Build queued.
            You can see the status of your build at
            https://platform.bymason.com/controller/projects/project-id

            Build completed.
        """))

    def test__stage__no_files_fails(self):
        result = self.runner.invoke(cli, ['stage'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__stage__non_existent_file_fails(self):
        result = self.runner.invoke(cli, ['stage', 'foobar'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__stage__no_creds_fails(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['stage', config_file], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__stage__negative_confirmation_aborts(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, ['stage', config_file], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            --------- OS Config ---------
            File Name: {}
            File size: 184
            Name: project-id
            Version: 1
            -----------------------------
            Continue register? [Y/n]: n
            Aborted!
        """.format(config_file)))

    def test__stage__file_is_registered(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        api = MagicMock()
        config = Config(
            auth_store=self._initialized_auth_store(),
            endpoints_store=self._initialized_endpoints_store(),
            api=api
        )

        result = self.runner.invoke(cli, ['stage', config_file], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            --------- OS Config ---------
            File Name: {}
            File size: 184
            Name: project-id
            Version: 1
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id' registered.

            Build queued.
            You can see the status of your build at
            https://platform.bymason.com/controller/projects/project-id
        """.format(config_file)))

    def test__stage__config_is_registered_and_awaits_build_completion(self):
        config_file = os.path.join(__tests_root__, 'res/config.yml')
        api = MagicMock()
        api.get_build = MagicMock(return_value={'data': {'status': 'COMPLETED'}})
        config = Config(
            auth_store=self._initialized_auth_store(),
            endpoints_store=self._initialized_endpoints_store(),
            api=api
        )

        result = self.runner.invoke(cli, ['stage', '--await', config_file], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            --------- OS Config ---------
            File Name: {}
            File size: 184
            Name: project-id
            Version: 1
            -----------------------------
            Continue register? [Y/n]: 
            Config 'project-id' registered.

            Build queued.
            You can see the status of your build at
            https://platform.bymason.com/controller/projects/project-id

            Build completed.
        """.format(config_file)))

    def test__deploy_config__invalid_name_fails(self):
        result = self.runner.invoke(cli, ['deploy', 'config', 'project-id', 'invalid', 'group'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__deploy_config__no_group_fails(self):
        result = self.runner.invoke(cli, ['deploy', 'config', 'project-id', '1'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__deploy_config__no_creds_fails(self):
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'config',
            'project-id', '1', 'group'
        ], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__deploy_config__non_existant_latest_config_fails(self):
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value=None)
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'config',
            'project-id', 'latest', 'group'
        ], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Config 'project-id' not found, register it first.
            Aborted!
        """))

    def test__deploy_config__negative_confirmation_aborts(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'config',
            'project-id', '1', 'group'
        ], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: project-id
            Type: config
            Version: 1
            Group: group
            Push: False
            -----------------------------
            Continue deploy? [Y/n]: n
            Aborted!
        """))

    def test__deploy_config__config_is_deployed(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'config',
            'project-id', '1', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: project-id
            Type: config
            Version: 1
            Group: group
            Push: False
            -----------------------------
            Continue deploy? [Y/n]: 
            Config 'project-id' deployed.
        """))

    def test__deploy_config__latest_config_is_deployed(self):
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value={'version': '42'})
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'config',
            'project-id', 'latest', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: project-id
            Type: config
            Version: 42
            Group: group
            Push: False
            -----------------------------
            Continue deploy? [Y/n]: 
            Config 'project-id' deployed.
        """))

    def test__deploy_config__warning_is_logged_when_no_https_flag_is_used(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', '--no-https', 'config',
            'project-id', '1', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: project-id
            Type: config
            Version: 1
            Group: group
            Push: False
    
            ***WARNING***
            --no-https enabled: this deployment will be delivered to devices over HTTP.
            ***WARNING***
            -----------------------------
            Continue deploy? [Y/n]: 
            Config 'project-id' deployed.
        """))

    def test__deploy_apk__invalid_name_fails(self):
        result = self.runner.invoke(cli, ['deploy', 'apk', 'com.example.app', 'invalid', 'group'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__deploy_apk__no_group_fails(self):
        result = self.runner.invoke(cli, ['deploy', 'apk', 'com.example.app', '1'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__deploy_apk__no_creds_fails(self):
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'apk',
            'com.example.app', '1', 'group'
        ], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__deploy_apk__non_existant_latest_apk_fails(self):
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value=None)
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'apk',
            'com.example.app', 'latest', 'group'
        ], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Apk 'com.example.app' not found, register it first.
            Aborted!
        """))

    def test__deploy_apk__negative_confirmation_aborts(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'apk',
            'com.example.app', '1', 'group'
        ], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: com.example.app
            Type: apk
            Version: 1
            Group: group
            Push: False
            -----------------------------
            Continue deploy? [Y/n]: n
            Aborted!
        """))

    def test__deploy_apk__apk_is_deployed(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'apk',
            'com.example.app', '1', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: com.example.app
            Type: apk
            Version: 1
            Group: group
            Push: False
            -----------------------------
            Continue deploy? [Y/n]: 
            Apk 'com.example.app' deployed.
        """))

    def test__deploy_apk__latest_apk_is_deployed(self):
        api = MagicMock()
        api.get_latest_artifact = MagicMock(return_value={'version': '42'})
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'apk',
            'com.example.app', 'latest', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: com.example.app
            Type: apk
            Version: 42
            Group: group
            Push: False
            -----------------------------
            Continue deploy? [Y/n]: 
            Apk 'com.example.app' deployed.
        """))

    def test__deploy_apk__warning_is_logged_when_no_https_flag_is_used(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', '--no-https', 'apk',
            'com.example.app', '1', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: com.example.app
            Type: apk
            Version: 1
            Group: group
            Push: False
    
            ***WARNING***
            --no-https enabled: this deployment will be delivered to devices over HTTP.
            ***WARNING***
            -----------------------------
            Continue deploy? [Y/n]: 
            Apk 'com.example.app' deployed.
        """))

    def test__deploy_ota__no_group_fails(self):
        result = self.runner.invoke(cli, ['deploy', 'ota', 'mason-os', '1'])

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 2)

    def test__deploy_ota__no_creds_fails(self):
        api = MagicMock()
        config = Config(auth_store=self._uninitialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'ota',
            'mason-os', '2.0.0', 'group'
        ], obj=config)

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            error: Not authenticated. Run 'mason login' to sign in.
            Aborted!
        """))

    def test__deploy_ota__negative_confirmation_aborts(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'ota',
            'mason-os', '2.0.0', 'group'
        ], obj=config, input='n')

        self.assertIsInstance(result.exception, SystemExit)
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: mason-os
            Type: ota
            Version: 2.0.0
            Group: group
            Push: False
            -----------------------------
            Continue deploy? [Y/n]: n
            Aborted!
        """))

    def test__deploy_ota__ota_is_deployed(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', 'ota',
            'mason-os', '2.0.0', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: mason-os
            Type: ota
            Version: 2.0.0
            Group: group
            Push: False
            -----------------------------
            Continue deploy? [Y/n]: 
            Ota 'mason-os' deployed.
        """))

    def test__deploy_ota__warning_is_logged_when_no_https_flag_is_used(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', '--no-https', 'ota',
            'mason-os', '2.0.0', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            ---------- DEPLOY -----------
            Name: mason-os
            Type: ota
            Version: 2.0.0
            Group: group
            Push: False
    
            ***WARNING***
            --no-https enabled: this deployment will be delivered to devices over HTTP.
            ***WARNING***
            -----------------------------
            Continue deploy? [Y/n]: 
            Ota 'mason-os' deployed.
        """))

    def test__deploy_ota__warning_is_logged_when_invalid_name(self):
        api = MagicMock()
        config = Config(auth_store=self._initialized_auth_store(), api=api)

        result = self.runner.invoke(cli, [
            'deploy', '--no-https', 'ota',
            'invalid', '2.0.0', 'group'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            warning: Unknown name 'invalid' for 'ota' deployments. Forcing it to 'mason-os'
            ---------- DEPLOY -----------
            Name: mason-os
            Type: ota
            Version: 2.0.0
            Group: group
            Push: False
    
            ***WARNING***
            --no-https enabled: this deployment will be delivered to devices over HTTP.
            ***WARNING***
            -----------------------------
            Continue deploy? [Y/n]: 
            Ota 'mason-os' deployed.
        """))

    def test__login__saves_creds(self):
        with self.runner.isolated_filesystem():
            auth_store = Store('fake-auth', {}, os.path.abspath(''), False)
        api = MagicMock()
        api.login = MagicMock(return_value={'id_token': 'id', 'access_token': 'access'})
        config = Config(auth_store=auth_store, api=api)

        result = self.runner.invoke(cli, [
            'login',
            '--token', 'Foobar',
            '--username', 'name',
            '--password', 'pass'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            Successfully logged in.
        """.format(__version__)))

        auth_store.clear()
        auth_store.restore()
        self.assertDictEqual(auth_store._fields, {
            'api_key': 'Foobar',
            'id_token': 'id',
            'access_token': 'access'
        })

    def test__login__empty_api_key_is_ignored(self):
        with self.runner.isolated_filesystem():
            auth_store = Store('fake-auth', {}, os.path.abspath(''), False)
            auth_store['api_key'] = 'Foobar'
            auth_store.save()
        api = MagicMock()
        api.login = MagicMock(return_value={'id_token': 'id', 'access_token': 'access'})
        config = Config(auth_store=auth_store, api=api)

        result = self.runner.invoke(cli, [
            'login',
            '--username', 'name',
            '--password', 'pass'
        ], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

        auth_store.clear()
        auth_store.restore()
        self.assertDictEqual(auth_store._fields, {
            'api_key': 'Foobar',
            'id_token': 'id',
            'access_token': 'access'
        })

    def test__logout__clears_creds(self):
        with self.runner.isolated_filesystem():
            auth_store = Store('fake-auth', {}, os.path.abspath(''), False)
            auth_store['apk_key'] = 'Foobar'
            auth_store.save()
        config = Config(auth_store=auth_store)

        result = self.runner.invoke(cli, ['logout'], obj=config)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(inspect.cleandoc(result.output), inspect.cleandoc("""
            Successfully logged out.
        """.format(__version__)))

        auth_store.restore()
        self.assertIsNone(auth_store['apk_key'])

    def _uninitialized_auth_store(self):
        with self.runner.isolated_filesystem():
            return Store('fake-auth', {}, os.path.abspath(''), False)

    def _initialized_auth_store(self):
        with self.runner.isolated_filesystem():
            auth_store = Store('fake-auth', {}, os.path.abspath(''), False)

            auth_store['api_key'] = 'key'
            auth_store['id_token'] = 'id'
            auth_store['access_token'] = 'access'

            return auth_store

    def _initialized_endpoints_store(self):
        endpoints_store = MagicMock()
        endpoints_store.__getitem__ = MagicMock(return_value='https://platform.bymason.com')
        return endpoints_store

    @contextlib.contextmanager
    def _cd(self, dir):
        cwd = os.getcwd()
        os.chdir(dir)
        try:
            yield dir
        finally:
            os.chdir(cwd)

    @contextlib.contextmanager
    def _home_dir_isolated_filesystem(self):
        cwd = os.getcwd()
        t = os.path.join(os.path.expanduser('~'), '.cache/tmp-mason-tests')
        if not os.path.exists(t):
            os.makedirs(t)
        os.chdir(t)
        try:
            yield t
        finally:
            os.chdir(cwd)
            try:
                shutil.rmtree(t)
            except (OSError, IOError):
                pass
