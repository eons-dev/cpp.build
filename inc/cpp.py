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
        this.optionalKWArgs["cmake_version"] = "3.1.1"
        this.optionalKWArgs["file_name"] = None
        this.optionalKWArgs["libs_shared"] = None

        this.supportedProjectTypes.append("lib")
        this.supportedProjectTypes.append("mod")
        this.supportedProjectTypes.append("bin")
        this.supportedProjectTypes.append("srv")
        this.supportedProjectTypes.append("test")

        this.valid_cxx_extensions = [
            ".cpp",
            ".h"
        ]
        this.valid_lib_extensions = [
            ".a",
            ".so"
        ]

    # Required Builder method. See that class for details.
    def DidBuildSucceed(this):
        result = os.path.join(this.packagePath,this.file_name)
        logging.debug(f"Checking if build was successful; output should be {result}")
        return os.path.isfile(result)

    # Required Builder method. See that class for details.
    def Build(this):
        if (this.file_name is None):
            this.file_name = this.projectName

        this.packagePath = os.path.join(this.buildPath, "out")
        mkpath(this.packagePath)

        logging.debug(f"Building in {this.buildPath}")
        logging.debug(f"Packaging in {this.packagePath}")

        this.GenCMake()
        this.CMake(".")
        this.Make()

        # include header files with libraries
        if (this.projectType in ["lib"]):
            copy_tree(this.incPath, this.packagePath)

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
            if not os.path.isfile(os.path.join(directory, file)):
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
set (CMAKE_CXX_STANDARD {this.cpp_version})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY {this.packagePath})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY {this.packagePath})
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY {this.packagePath})
''')

        cmakeFile.write(f"project({this.file_name})\n")

        if (this.incPath is not None):
            cmakeFile.write(f"include_directories({this.incPath})\n")

        if (this.projectType in ["bin", "test", "srv"]):
            logging.info("Addind binary specific code")

            cmakeFile.write(f"add_executable({this.file_name} {this.GetSourceFiles(this.srcPath)})\n")

        if (this.projectType in ["lib", "mod"]):
            logging.info("Adding library specific code")

            # #TODO: support windows install targets
            installSrcPath = f"/usr/local/lib"
            installIncPath = f"/usr/local/include/{this.file_name}"

            cmakeFile.write(f"add_library ({this.file_name} SHARED {this.GetSourceFiles(this.srcPath)})\n")
            cmakeFile.write(
                f"set_target_properties({this.file_name} PROPERTIES PUBLIC_HEADER \"{this.GetSourceFiles(this.incPath, ';')}\")\n")
            cmakeFile.write(
                f"INSTALL(TARGETS {this.file_name} LIBRARY DESTINATION {installSrcPath} PUBLIC_HEADER DESTINATION {installIncPath})\n")

        cmakeFile.write(f'''
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)
target_link_libraries({this.file_name} Threads::Threads)
''')
        if (this.libPath is not None):
            cmakeFile.write(f"include_directories({this.libPath})\n")
            cmakeFile.write(f"target_link_directories({this.file_name} PUBLIC {this.libPath}))\n")
            cmakeFile.write(f"target_link_libraries({this.file_name} {this.GetLibs(this.libPath)})\n")

        if (this.libs_shared is not None):
            cmakeFile.write(f"target_link_libraries({this.file_name} {' '.join(this.libs_shared)})\n")

        cmakeFile.close()

    def CMake(this, path):
        this.RunCommand(f"cmake {path}")

    def Make(this):
        this.RunCommand("make")

