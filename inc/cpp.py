import os
import logging
import shutil
import jsonpickle
from distutils.file_util import copy_file
from distutils.dir_util import copy_tree, mkpath
from ebbs import Builder


# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class cpp(Builder):
    def __init__(this, name="C++ Builder"):
        super().__init__(name)

        this.clearBuildPath = True

        this.optionalKWArgs["cpp_version"] = 11
        this.optionalKWArgs["cmake_version"] = "3.12.0"
        this.optionalKWArgs["file_name"] = None
        this.optionalKWArgs["dep_lib"] = None
        this.optionalKWArgs["output_dir"] = "out"
        this.optionalKWArgs["toolchain"] = None
        this.optionalKWArgs["toolchain_dir"] = "tool"
        this.optionalKWArgs["define"] = None
        this.optionalKWArgs["build_type"] = "Debug"
        this.optionalKWArgs["install_bin_to"] = "/usr/local/bin"
        this.optionalKWArgs["install_inc_to"] = "/usr/local/include"
        this.optionalKWArgs["install_lib_to"] = "/usr/local/lib"

        this.supportedProjectTypes.append("lib")
        this.supportedProjectTypes.append("mod")
        this.supportedProjectTypes.append("bin")
        this.supportedProjectTypes.append("srv")
        this.supportedProjectTypes.append("test")

        this.valid_cxx_extensions = [
            ".c",
            ".cpp",
            ".h",
            ".hpp"
        ]
        this.valid_lib_extensions = [
            ".a",
            ".so"
        ]

    # Required Builder method. See that class for details.
    def DidBuildSucceed(this):
        result = this.packagePath
        logging.debug(f"Checking if build was successful; output should be in {result}")
        return bool(os.listdir(result))

    # Required Builder method. See that class for details.
    def Build(this):
        if (this.file_name is None):
            this.file_name = this.projectName

        this.projectIsLib = False
        if (this.projectType in ["lib", "mod"]):
            this.projectIsLib = True

        this.packagePath = os.path.join(this.buildPath, this.output_dir)
        mkpath(this.packagePath)

        this.toolPath = os.path.join(this.buildPath, this.toolchain_dir)

        logging.debug(f"Building in {this.buildPath}")
        logging.debug(f"Packaging in {this.packagePath}")

        this.GenCMake()

        if (this.projectIsLib):
            this.GenSingleHeader()

        this.CMake(".")
        this.Make()

        # include header files with libraries
        if (this.projectIsLib):
            copy_tree(this.incPath, this.packagePath)

        # this.GenInstall()

    def GetSourceFiles(this, directory, seperator=" "):
        ret = ""
        for root, dirs, files in os.walk(directory):
            for f in files:
                name, ext = os.path.splitext(f)
                if (ext in this.valid_cxx_extensions):
                    # logging.info(f"    {os.path.join(root, f)}")
                    ret += f"{os.path.join(root, f)}{seperator}"
        return ret[:-1]

    def GetLibs(this, directory, seperator=" "):
        ret = ""
        for file in os.listdir(directory):
            if (not os.path.isfile(os.path.join(directory, file))):
                continue
            name, ext = os.path.splitext(file)
            if (ext in this.valid_lib_extensions):
                ret += (f"{name[3:]}{seperator}")
        return ret[:-1]

    def GenCMake(this):
        # Write our cmake file
        cmakeFile = open("CMakeLists.txt", "w")

        cmakeFile.write(f'''
cmake_minimum_required (VERSION {this.cmake_version})
set(CMAKE_CXX_STANDARD {this.cpp_version})
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY {this.packagePath})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY {this.packagePath})
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY {this.packagePath})
set(CMAKE_BUILD_TYPE {this.build_type}) 
''')

        if (this.toolchain is not None):

            # Make sure we have the toolchain.
            if (not os.path.isdir(this.toolPath)):
                toolchainSourcePath = os.path.join(this.executor.repo.store,f"toolchain_{this.toolchain}")
                if (not os.path.isdir(toolchainSourcePath)):
                    this.executor.DownloadPackage(f"toolchain_{this.toolchain}", registerClasses=False, createSubDirectory=True)
                copy_tree(toolchainSourcePath, this.toolPath)

            toolchainCmakeFile = f"{os.path.join(this.toolPath,this.toolchain)}.cmake"
            if (not os.path.isfile(toolchainCmakeFile)):
                raise OtherBuildError(f"Could not find cmake file: {toolchainCmakeFile}")
            toolchainBinPath = os.path.join(this.toolPath, "bin")
            cmakeFile.write(f"set(CROSS_TARGET_TOOLCHAIN_PATH {toolchainBinPath})\n")
            cmakeFile.write(f"set(CMAKE_TOOLCHAIN_FILE {toolchainCmakeFile})\n")

        cmakeFile.write(f"project({this.file_name})\n")

        if (this.incPath is not None):
            cmakeFile.write(f"include_directories({this.incPath})\n")

        if (this.projectIsLib):
            logging.info("Adding library specific code")
            cmakeFile.write(f"add_library ({this.file_name} SHARED {this.GetSourceFiles(this.srcPath)})\n")
        else:
            logging.info("Adding binary specific code")
            cmakeFile.write(f"add_executable({this.file_name} {this.GetSourceFiles(this.srcPath)})\n")

        if (this.define is not None):
            cmakeFile.write(f"add_compile_definitions(")
            for key, value in this.define.items():
                if (not value):
                    cmakeFile.write(f"{key}")
                else:
                    cmakeFile.write(f"{key}={value}")
                cmakeFile.write(" ")
            cmakeFile.write(")\n")

        cmakeFile.write(f'''
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)
target_link_libraries({this.file_name} Threads::Threads)
''')
        if (this.libPath is not None):
            cmakeFile.write(f"include_directories({this.libPath})\n")
            cmakeFile.write(f"target_link_directories({this.file_name} PUBLIC {this.libPath}))\n")
            cmakeFile.write(f"target_link_libraries({this.file_name} {this.GetLibs(this.libPath)})\n")

        if (this.dep_lib is not None):
            cmakeFile.write(f"target_link_libraries({this.file_name} {' '.join(this.dep_lib)})\n")
            cmakeFile.write('set(CMAKE_CXX_LINK_EXECUTABLE "<CMAKE_CXX_COMPILER>  <FLAGS> <CMAKE_CXX_LINK_FLAGS> <LINK_FLAGS> <OBJECTS> -o <TARGET> -Wl,--start-group -Wl,--whole-archive <LINK_LIBRARIES> -Wl,--no-whole-archive -Wl,--end-group")') #per https://stackoverflow.com/questions/53071878/using-whole-archive-linker-option-with-cmake-and-libraries-with-other-library

        cmakeFile.close()


    def GenSingleHeader(this):
        includes = this.GetSourceFiles(this.incPath).split(' ')
        includes = [os.path.relpath(path, this.incPath) for path in includes]

        singleHeaderFile = open(os.path.join(this.packagePath,f"{this.projectName}.h"), "w+")
        singleHeaderFile.write('#pragma once\n')
        for i in includes:
            singleHeaderFile.write(f"#include <{i}>\n")

        singleHeaderFile.close()


        # Create install.json, which will be used by emi to install what we've built.
        # TODO: why not just use jsonpickle?
    def GenInstall(this):
        files = []
        dirs = []
        for thing in os.listdir(this.packagePath):
            if (os.path.isdir(thing)):
                dirs.append(thing)
            else:
                files.append(thing)

        installFile = open(os.path.join(this.packagePath,"install.json"), "w+")
        installFile.write('{\n')

        if (this.dep_lib is not None):
            installFile.write('    dep: [\n')
            for i, d in enumerate(this.dep_lib):
                installFile.write(f'        {d}')
                if (i != len(files)-1):
                    installFile.write(',\n')
                else:
                    installFile.write('\n')
            installFile.write('    ],\n')

        if (not this.projectIsLib):
            installFile.write('    bin: [\n')

            for i, f in enumerate(files):
                installFile.write(f'        {f}')
                if (i != len(files)-1):
                    installFile.write(',\n')
                else:
                    installFile.write('\n')

            for i, d in enumerate(dirs):
                installFile.write(f'        {d}')
                if (i != len(files)-1):
                    installFile.write(',\n')
                else:
                    installFile.write('\n')

            installFile.write('    ]\n')

        if (this.projectIsLib):

            #FIXME: THIS NEEDS WORK.

            # Separate library files from include files.
            # NOTE: this only parses files in the root of packagePath, not recursively.

            includes = []
            libraries = []

            for f in files:
                name, ext = os.path.splitext(f)
                if (ext in this.valid_lib_extensions):
                    libraries.append(f)
                else:
                    includes.append(f)

            installFile.write('{\n')
            installFile.write('    lib: [\n')

            for i, f in enumerate(libraries):
                installFile.write(f'        {f}')
                if (i != len(files)-1):
                    installFile.write(',\n')
                else:
                    installFile.write('\n')

            installFile.write('    ],\n')
            installFile.write('    inc: [\n')

            for i, thing in enumerate(dirs + includes):
                installFile.write(f'        {thing}')
                if (i != len(files)-1):
                    installFile.write(',\n')
                else:
                    installFile.write('\n')

            installFile.write('    ]\n')

        installFile.write('}\n')
        installFile.close()


    def CMake(this, path):
        this.RunCommand(f"cmake {path}")


    def Make(this):
        this.RunCommand("make")
