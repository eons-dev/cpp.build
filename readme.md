# EBBS C++ Builder

Instead of writing and managing cmake files throughout your directory tree, you can use `ebbs -b cpp` and all .h and .cpp files in your source tree will be discovered and added to a CMakeLists.txt, which is then built with cmake and make, so you get the compiled product you want.

When using this system, we recommend (but do not require) you comply with all [eons conventions](https://eons.llc/convention/): specifically, [the one stating that all files should be used on all build targets](https://eons.llc/convention/single-file-for-all-targets/).

Supported project types:
* lib
* bin
* test (alias for bin, for tests)
* srv (alias for bin, for a web server)
* mod (alias for lib, for lib-dependent modules)

Prerequisites:
* cmake >= 3.12.0 (can be less but not all config features will be supported)
* make >= whatever
* g++ or equivalent

## Configuration

You may wish to create an EBBS config.json in a build folder within your project for additional configuration (i.e. a simplified version of CMakeLists.txt)
You can include things like
```json
{
  "name" : "my-exe or my-lib",
  "cpp_version" : 17,
  "dep_lib": [
    "shared",
    "libraries",
    "to",
    "link"
  ]
}
```
You can also set up a multi-stage build pipeline with EBBS's "next". See [ebbs](https://github.com/eons-dev/bin_ebbs) for more info.
For an example, check out the [infrastructure.tech web server](https://github.com/infrastructure-tech/srv_infrastructure)