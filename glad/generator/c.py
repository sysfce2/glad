from glad.generator import Generator
from glad.generator.util import makefiledir
import os.path


class CGenerator(Generator):
    def open(self):
        suffix = ''
        if not self.api == 'gl':
            suffix = '_{}'.format(self.api)

        self.h_include = '<glad/glad{}.h>'.format(suffix)
        self._f_c = open(make_path(self.path, 'src',
                                   'glad{}.c'.format(suffix)), 'w')
        self._f_h = open(make_path(self.path, 'include',
                                   'glad', 'glad{}.h'.format(suffix)), 'w')
        return self

    def close(self):
        self._f_c.close()
        self._f_h.close()

    def generate_loader(self, features, extensions):
        f = self._f_c

        for feature in features:
            f.write('static void load_{}(LOADER load) {{\n'
                    .format(feature.name))
            f.write('\tif(!{}) return;\n'.format(feature.name))
            for func in feature.functions:
                f.write('\t{name} = (fp_{name})load("{name}");\n'
                    .format(name=func.proto.name))
            f.write('\treturn;\n}\n\n')

        for ext in extensions:
            if len(list(ext.functions)) == 0:
                continue

            f.write('static int load_{}(LOADER load) {{\n'
                .format(ext.name))
            f.write('\tif(!{}) return 0;\n'.format(ext.name))
            for func in ext.functions:
                # even if they were in written we need to load it
                f.write('\t{name} = (fp_{name})load("{name}");\n'
                    .format(name=func.proto.name))
            f.write('\treturn 1;\n')
            f.write('}\n')

        f.write('static void find_extensions(void) {\n')
        for ext in extensions:
            f.write('\t{0} = has_ext("{0}");\n'.format(ext.name))
        f.write('}\n\n')

        f.write('static void find_core(void) {\n')
        self.loader.write_find_core(f)
        for feature in features:
            f.write('\t{} = (major == {num[0]} && minor >= {num[1]}) ||'
                ' major > {num[0]};\n'.format(feature.name, num=feature.number))
        f.write('}\n\n')

        f.write('void gladLoadGLLoader(LOADER load) {\n')

        self.loader.write_begin_load(f)
        f.write('\tfind_core();\n')

        for feature in features:
            f.write('\tload_{}(load);\n'.format(feature.name))
        f.write('\n\tfind_extensions();\n')
        for ext in extensions:
            if len(list(ext.functions)) == 0:
                continue
            f.write('\tload_{}(load);\n'.format(ext.name))
        f.write('\n\treturn;\n}\n\n')

        self.loader.write_header_end(self._f_h)

    def generate_types(self, types):
        f = self._f_h

        self.loader.write_header(f)

        for type in types:
            if self.api == 'gl' and 'khrplatform' in type.raw:
                continue

            f.write(type.raw.lstrip().replace('        ', ''))
            f.write('\n')

    def generate_features(self, features):
        written = set()
        write = set()

        f = self._f_h
        for feature in features:
            for enum in feature.enums:
                if not enum in written:
                    f.write('#define {} {}\n'.format(enum.name, enum.value))
                written.add(enum)

        for feature in features:
            f.write('int {};\n'.format(feature.name))
            for func in feature.functions:
                if not func in written:
                    self.write_function_prototype(f, func)
                    write.add(func)
                written.add(func)

        f = self._f_c
        f.write('#include <string.h>\n#include {}\n'.format(self.h_include))
        self.loader.write(f)
        self.loader.write_has_ext(f)

        for func in write:
            self.write_function(f, func)


    def generate_extensions(self, extensions, enums, functions):
        write = set()
        written = set(enum.name for enum in enums) | \
                    set(function.proto.name for function in functions)

        f = self._f_h
        for ext in extensions:
            f.write('int {};\n'.format(ext.name))
            for enum in ext.enums:
                if not enum.name in written:
                    f.write('#define {} {}\n'.format(enum.name, enum.value))
                written.add(enum.name)

            for func in ext.functions:
                if not func.proto.name in written:
                    self.write_function_prototype(f, func)
                    write.add(func)
                written.add(func.proto.name)

        f = self._f_c
        for func in write:
            self.write_function(f, func)


    def write_function_prototype(self, fobj, func):
        fobj.write('typedef {} (* fp_{})({});\n'.format(func.proto.ret.to_c(),
                                                      func.proto.name,
                        ', '.join(param.type.to_c() for param in func.params)))
        fobj.write('extern fp_{0} glad{0};\n'.format(func.proto.name))
        fobj.write('#define {0} glad{0}\n'.format(func.proto.name))

    def write_function(self, fobj, func):
        fobj.write('fp_{0} glad{0};\n'.format(func.proto.name))


def make_path(path, *args):
    path = os.path.join(path, *args)
    makefiledir(path)
    return path
