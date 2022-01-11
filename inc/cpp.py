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

        self.clearBuildPath = True

        self.requiredKWArgs.append()

        self.optionalKWArgs.["cpp_version"] = 11
        self.optionalKWArgs.["cmake_version"] = "3.1.1"
        self.optionalKWArgs.["name"] = "REPLACEME"
        self.optionalKWArgs.["libs_shared"] = None

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
        result = os.path.join(self.packagePath,self.name)
        logging.debug(f"Checking if build was successful; output should be {result}")
        return os.path.isfile(result)

    # Required Builder method. See that class for details.
    def Build(self):
        if (self.name == "C++ Builder"):
            self.name = self.projectName

        self.packagePath = os.path.join(self.buildPath, "out")
        mkpath(self.packagePath)

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
        cmakeFile = open("CMakeLists.txt", "w")

        cmakeFile.write(f'''
cmake_minimum_required (VERSION {self.cmake_version})
set (CMAKE_CXX_STANDARD {self.cpp_version})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY {self.packagePath})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY {self.packagePath})
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY {self.packagePath})
''')

        cmakeFile.write(f"project({self.name})\n")

        if (self.incPath is not None):
            cmakeFile.write(f"include_directories({self.incPath})\n")

        if (self.projectType in ["bin", "test", "srv"]):
            logging.info("Addind binary specific code")

            cmakeFile.write(f"add_executable({self.name} {self.GetSourceFiles(self.srcPath)})\n")

        if (self.projectType in ["lib", "mod"]):
            logging.info("Adding library specific code")

            # #TODO: support windows install targets
            installSrcPath = f"/usr/local/lib"
            installIncPath = f"/usr/local/include/{self.name}"

            cmakeFile.write(f"add_library ({self.name} SHARED {self.GetSourceFiles(self.srcPath)})\n")
            cmakeFile.write(
                f"set_target_properties({self.name} PROPERTIES PUBLIC_HEADER \"{self.GetSourceFiles(self.incPath, ';')}\")\n")
            cmakeFile.write(
                f"INSTALL(TARGETS {self.name} LIBRARY DESTINATION {installSrcPath} PUBLIC_HEADER DESTINATION {installIncPath})\n")

        cmakeFile.write(f'''
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)
target_link_libraries({self.name} Threads::Threads)
''')
        if (self.libPath is not None):
            cmakeFile.write(f"include_directories({self.libPath})\n")
            cmakeFile.write(f"target_link_directories({self.name} PUBLIC {self.libPath}))\n")
            cmakeFile.write(f"target_link_libraries({self.name} {self.GetLibs(self.libPath)})\n")

        if (self.libs_shared is not None):
            cmakeFile.write(f"target_link_libraries({self.name} {' '.join(self.libs_shared)})\n")

        cmakeFile.close()

    def CMake(self, path):
        self.RunCommand(f"cmake {path}")

    def Make(self):
        self.RunCommand("make")

