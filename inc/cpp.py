import os
import logging
import shutil
import jsonpickle
from distutils.file_util import copy_file
from distutils.dir_util import copy_tree, mkpath
from ebbs import Builder


# Class name is what is used at cli, so we defy convention here in favor of ease-of-use.
class cpp(Builder):
    def __init__(self, name="C++ Builder"):
        super().__init__(name)

        self.supportedProjectTypes.append("lib")
        self.supportedProjectTypes.append("mod")
        self.supportedProjectTypes.append("bin")
        self.supportedProjectTypes.append("srv")
        self.supportedProjectTypes.append("test")

        self.valid_cxx_extensions = [
            ".cpp",
            ".h"
        ]
        self.valid_lib_extensions = [
            ".a",
            ".so"
        ]

    # Required Builder method. See that class for details.
    def DidBuildSucceed(self):
        result = os.path.join(self.packagePath,self.packageName)
        logging.debug(f"Checking if build was successful; output should be {result}")
        return os.path.isfile(result)

    # Required Builder method. See that class for details.
    def Build(self):
        config_file = open(os.path.join(self.rootPath, "config.json"), "r")
        self.config = jsonpickle.decode(config_file.read())

        self.buildPath = os.path.join(self.rootPath, self.buildPath)
        if (os.path.exists(self.buildPath)):
            logging.info(f"DELETING {self.buildPath}")
            shutil.rmtree(self.buildPath)
        mkpath(self.buildPath)
        os.chdir(self.buildPath)

        self.packageName = self.projectName;
        if ("name" in self.config):
            self.packageName = self.config["name"]

        self.packagePath = os.path.join(self.buildPath, "out")
        mkpath(self.packagePath)

        self.cpp_version = 11;
        if ("cpp_version" in self.config):
            self.cpp_version = self.config["cpp_version"]

        self.cmake_version = "3.1.1";
        if ("cmake_version" in self.config):
            self.cmake_version = self.config["cmake_version"]

        logging.debug(f"Building in {self.buildPath}")
        logging.debug(f"Packaging in {self.packagePath}")

        self.GenCMake()
        self.CMake(".")
        self.Make()

        # include header files with libraries
        if (self.projectType in ["lib"]):
            copy_tree(self.incPath, self.packagePath)

    def GetSourceFiles(self, directory, seperator=" "):
        ret = ""
        for root, dirs, files in os.walk(directory):
            for f in files:
                name, ext = os.path.splitext(f)
                if (ext in self.valid_cxx_extensions):
                    # logging.info(f"    {os.path.join(root, f)}")
                    ret += f"{os.path.join(root, f)}{seperator}"
        return ret[:-1]

    def GetLibs(self, directory, seperator=" "):
        ret = ""
        for file in os.listdir(directory):
            if not os.path.isfile(os.path.join(directory, file)):
                continue
            name, ext = os.path.splitext(file)
            if (ext in self.valid_lib_extensions):
                ret += (f"{name[3:]}{seperator}")
        return ret[:-1]

    def GenCMake(self):
        # Write our cmake file
        cmake_file = open("CMakeLists.txt", "w")

        cmake_file.write(f'''
cmake_minimum_required (VERSION {self.cmake_version})
set (CMAKE_CXX_STANDARD {self.cpp_version})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY {self.packagePath})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY {self.packagePath})
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY {self.packagePath})
''')

        cmake_file.write(f"project({self.packageName})\n")

        if (self.incPath is not None):
            cmake_file.write(f"include_directories({self.incPath})\n")

        if (self.projectType in ["bin", "test", "srv"]):
            logging.info("Addind binary specific code")

            cmake_file.write(f"add_executable({self.packageName} {self.GetSourceFiles(self.srcPath)})\n")

        if (self.projectType in ["lib", "mod"]):
            logging.info("Adding library specific code")

            # #TODO: support windows install targets
            installSrcPath = f"/usr/local/lib"
            installIncPath = f"/usr/local/include/{self.packageName}"

            cmake_file.write(f"add_library ({self.packageName} SHARED {self.GetSourceFiles(self.srcPath)})\n")
            cmake_file.write(
                f"set_target_properties({self.packageName} PROPERTIES PUBLIC_HEADER \"{self.GetSourceFiles(self.incPath, ';')}\")\n")
            cmake_file.write(
                f"INSTALL(TARGETS {self.packageName} LIBRARY DESTINATION {installSrcPath} PUBLIC_HEADER DESTINATION {installIncPath})\n")

        cmake_file.write(f'''
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)
target_link_libraries({self.packageName} Threads::Threads)
''')
        if (self.libPath is not None):
            cmake_file.write(f"include_directories({self.libPath})\n")
            cmake_file.write(f"target_link_directories({self.packageName} PUBLIC {self.libPath}))\n")
            cmake_file.write(f"target_link_libraries({self.packageName} {self.GetLibs(self.libPath)})\n")

        if ("libs_shared" in self.config):
            cmake_file.write(f"target_link_libraries({self.packageName} {' '.join(self.config['libs_shared'])})\n")

        cmake_file.close()

    def CMake(self, path):
        self.RunCommand(f"cmake {path}")

    def Make(self):
        self.RunCommand("make")

