# EBBS C++ Builder

Instead of writing and managing cmake files throughout your directory tree, you can use `ebbs -l cpp` from a `build` folder and all .h and .cpp files in your source tree will be discovered and added to a CMakeLists.txt, which is then built with cmake and make, so you get the compiled product you want.

Supported project types:
* lib
* bin
* test (alias for bin, for tests)
* srv (alias for bin, for a web server)
* mod (alias for lib, for lib-dependent modules)

Prerequisites:
* cmake >= 3.1.1
* make >= whatever
* g++ or equivalent

Currently lacking support for auto-discovered tool chains and build targets - only compiles for the system it is run on.

## Configuration

You may wish to create a config.json in the root of your project for additional configuration (i.e. a simplified version of CMakeLists.txt)
You can include things like
```json
{
  "name" : "my-exe or my-lib",
  "cpp_version" : 17,
  "libs_shared": [
    "shared",
    "libraries",
    "to",
    "link"
  ]
}
```
You can also set up a multi-stage build pipeline with "ebbs_next". See [ebbs](https://github.com/eons-dev/bin_ebbs) for more info.
For an example, check out the [infrastructure.tech web server](https://github.com/infrastructure-tech/srv_infrastructure)