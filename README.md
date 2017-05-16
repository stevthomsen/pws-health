# Trunk Health Build
has multiple components.  The major components are:
*    startTrunkHealthBuild
*    subTrunkHealthBuild
*    trunk_health.rb

The Trunk Health Builds are set up to run from a cron job.  The final output is stored at http://peftech.vcd.hp.com/pws-external/ and is in the format of UTC_YYYY-MM-DD\_HH\_MM where all parts are UTC based.  Under the UTC directory is:
*    build_orchestrator.log
*    distro_1
*    .
*    .
*    .
*    distro_n

The log file, build_orchestrator.log, contains the messages about it's build including child threads and final status.  An example of one is:
<pre><code>
[  27831 ]              conductor - initialized.
[  27831 ]              conductor - start a new cycle.
[  27831 ] > [  27882 ] conductor - gave job 'limo_cp_lp3' to worker [ 27882 ].
[  27882 ] > [  27883 ] worker - gave job 'limo_cp_lp3' to worker [ 27883 ].
[  27885 ] > [  27886 ] worker - gave job 'limo_cp_mp1' to worker [ 27886 ].
[  27831 ] > [  27885 ] conductor - gave job 'limo_cp_mp1' to worker [ 27885 ].
[  27883 ]              worker - started job 'limo_cp_lp3'.
[  27886 ]              worker - started job 'limo_cp_mp1'.
[  27831 ] > [  27893 ] conductor - gave job 'limo_lp3' to worker [ 27893 ].
[  27893 ] > [  27894 ] worker - gave job 'limo_lp3' to worker [ 27894 ].
[  27831 ] > [  27899 ] conductor - gave job 'limo_mp1' to worker [ 27899 ].
[  27894 ]              worker - started job 'limo_lp3'.
[  27899 ] > [  27900 ] worker - gave job 'limo_mp1' to worker [ 27900 ].
[  27831 ] > [  27907 ] conductor - gave job 'maverickhidw_ofax_mp2' to worker [ 27907 ].
[  27900 ]              worker - started job 'limo_mp1'.
[  27907 ] > [  27908 ] worker - gave job 'maverickhidw_ofax_mp2' to worker [ 27908 ].
[  27908 ]              worker - started job 'maverickhidw_ofax_mp2'.
[  27883 ]              worker - completed job 'limo_cp_lp3'.
[  27886 ]              worker - completed job 'limo_cp_mp1'.
[  27908 ]              worker - completed job 'maverickhidw_ofax_mp2'.
[  27900 ]              worker - completed job 'limo_mp1'.
[  27894 ]              worker - completed job 'limo_lp3'.
[  27831 ]              conductor - workers have finished.
[  27831 ]              conductor - transfer workspace to gallery.
</code></pre>

An example of a distro listing is (this is for limo_lp3):
<pre><code>
build_limo_lp3.log
build_limo_lp3_ci_pkg_info.json
build_limo_lp3_report.json
limo_dist_lp3_002.thoms_20160801_103313_assert.all
limo_dist_lp3_002.thoms_20160801_103313_assert.dtb
limo_dist_lp3_002.thoms_20160801_103313_assert.yaml
limo_dist_lp3_002.thoms_20160801_103313_assert_boot_lbi_rootfs.fhx
limo_dist_lp3_002.thoms_20160801_103313_assert_boot_lbi_rootfs.fhx.info
limo_dist_lp3_002.thoms_20160801_103313_assert_datafs.fhx
limo_dist_lp3_002.thoms_20160801_103313_assert_datafs.fhx.info
limo_dist_lp3_002.thoms_20160801_103313_assert_sim_rootfs.fhx
limo_dist_lp3_002.thoms_20160801_103313_assert_sim_rootfs.fhx.info
limo_dist_lp3_002.thoms_20160801_103313_assert_sim_zImage*
limo_dist_lp3_002.thoms_20160801_103313_assert_sims
</code></pre>

## [startTrunkHealthBuild](#startTrunkHealthBuild)
is the main program used for Trunk Health Builds.  This program will call subTrunkHealthBuild for building each specified distributions.  They will be multiple invocations of subTrunkHealthBuild if multple distributions are to be built.  If you specify a distribution, only that distribution will be built.  You can supply multiple items for exclusion from the removal list (use mulitple -r's).  The removal list will be indentical for all distributions built.  This removal list is fed to subTrunkHealthBuild via stdin.
### [Syntax:](#Syntax) Here's the Usage message:
<pre><code>Usage: startTrunkHealthBuild
              -R &ltRS&gt:&ltRN&gt:PATH
              -C &ltPS&gt:&ltPN&gt:PATH
              &lt -O PATH &gt
              &lt -W PATH &gt
              &lt -T SECS &gt
              &lt -d DISTRO &gt
              &lt -r GLOB &gt
              &lt -u &gt
              &lt -h &gt

  Required Arugments:
      -R | --recipe_dir           Directory containing recipe files.
                                    basic usage:
                                      ':::/path/to/sirius_dist'
                                    advanced usage:
                                      'git@git.vcd.hp.com:sirius_dist:trunk:/path/to/sirius_dist'

      -C | --profile_dir          Directory continaing Trunk Health profiles.
                                    basic usage:
                                      ':::/path/to/profiles'
                                    advanced usage:
                                      'git@github.azc.ext.hp.com:ktang/pws-health-profiles:master:/path/to/profiles'

  Optional Arguments:
      -O | --output_dir           Directory to place build objects.
                                    default: 'pwd'

      -W | --workspace_base_dir   Temporary workspace directory.
                                    default: '/tmp/pws-health'

      -T | --max_retry_sec        Maximum seconds to wait before trying to run.
                                    default: ''

      -d | --distro               Specify a Trunk Health profile to build.  Repeatable.

      -u | --dump_removal_list    Print the list of items on the removal list and exit.

      -h | --help                 Output Usage message and exit.
</code></pre>

## [subTrunkHealthBuild](#subTrunkHealthBuild)
does the actual build for the specified distribution.  The removal list to be used is fed via stdin from startTrunkHealth  this removal list will trim space required for the every distribution to be built, after trunk_health.rb has run.  Then the remaining files are moved to it's final destination.  This script will call trunk_health.rb for the actual building.  All parameters are mandatory.
Here's the usage message:
<pre><code>Usage subTrunkHealthBuild:
    Specific-distro
    Recipe-dir
    Output-base-dir
    CI-yaml-dir
    Current-build-dir
    Temp-base-dir
    </code></pre>

## [trunk_health.rb](#trunk_health.rb)
does the underlying build of specified distribution from the specified YAML description.  All output files are created by this script and the scripts/executables called from here (i.e. makediist, opkg-make-index).
<pre><code>Usage: trunk_health.rb &ltoptions&gt

Supported options are:
  --allow-unsafe-reuse-of-output-dir
  --ci-pkg-info-log &ltx&gt                 Name of file to log information about the included CI packages. (JSON)
  --ci_yaml &ltx&gt                         Path to yaml-format CI dist config file
  --exit-on-warning                     Exit on a warning
  --makedist_opt &ltx&gt                  * Extra parameters for makedist
  --output_dir &ltx&gt                      Output path for distribution
  --recipe_dir &ltx&gt                      Path to directory containing recipe file

Options marked with '*' can appear more than once.

The ci_yaml file has the following contents
hw_phase: &ltphase label&gt
distribution: &ltname of distribution&gt
dist_recipe_reo: &ltname of git repo containing distribution recipe file&gt
dist_recipe_branch: &ltname of branch in git repo for recipe file&gt
ci_packages:
  - &ltci package to use in distribution&gt

If the distribution recipe name contains a hardware phase, the phase should
be specified as "_%p" in the recipe name.  Leave blank if the recipe and
packages do not have hardware phases.
The dist_recipe_repo and dist_recipe_branch fields are optional if a path
is specified for the command-line parameter recipe_dir.
The package name is the Sirius Hub package name with additional qualifiers
for build type (_%t, _%r) and hardware phase (_%p).  Packages that support
the build types ram_arel, ram_sarel, and ram_narel should use "_%r";
packages that support arel, sarel, and narel should use "_%t"; and
packages that support only service should use neither.  The end of the
package name specifies the major version number of the package.

Package examples:

  - package with hardware phase and ram_arel targets
    palermo_minus_sox_%p_%r,001
  - package with hardware phase and arel targets
    palermo_minus_nandboot_%p_%t,001
  - package without hardware phase and with arel targets
    palermo_minus_sol_general_%t,001
  - package without hardware phase and with service target
    palermo_minus-conf,001
	</code></pre>
