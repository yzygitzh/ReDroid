import csv
import os
import zipfile

def java_shorty2full(short_sig):
    basic_type_mapping = {
        "Z": "boolean",
        "B": "byte",
        "C": "char",
        "S": "short",
        "I": "int",
        "J": "long",
        "F": "float",
        "D": "double",
        "V": "void"
    }
    fields = short_sig.split()
    idx = 1
    array_depth = 0
    parsed_paras = []
    # while fields[1][idx] != ")":
    while idx < len(fields[1]):
        if fields[1][idx] == "L":
            class_end_idx = idx
            while fields[1][class_end_idx] != ";":
                class_end_idx += 1
            parsed_paras.append(fields[1][idx + 1:class_end_idx].replace("/", ".") + array_depth * "[]")
            idx = class_end_idx
            array_depth = 0
        elif fields[1][idx] == "[":
            array_depth += 1
        elif fields[1][idx] != ")":
            parsed_paras.append(basic_type_mapping[fields[1][idx]] + array_depth * "[]")
            array_depth = 0
        idx += 1
    return fields[0], parsed_paras

def java_full4dsm(shorty_sig):
    class_method, parsed_paras = java_shorty2full(shorty_sig)
    return class_method, parsed_paras[:-1], parsed_paras[-1]

def get_monitoring_methods(trace_item_list):
    ret_list = []
    # method_filter = set(["Z", "B", "C", "S", "I", "J", "Ljava/lang/String;"])
    # method_filter = set(["Z", "Ljava/lang/String;"])

    for trace_item in trace_item_list:
        fields = trace_item.split()
        sig = fields[1]
        sig_end = sig[sig.rfind(")") + 1:]
        #if sig_end in method_filter:
        ret_list.append(fields[0])
    return set(ret_list)

def extract_method_classes(methods_list):
    return sorted(list(set([
        ".".join(x.split(".")[:-1]) for x in methods_list
    ])))

def get_irrelevant_packages(irrelevant_packages):
    package_set = set()

    for jar_path in irrelevant_packages["jars"]:
        jar_file = zipfile.ZipFile(os.path.abspath(jar_path), "r")
        file_list = jar_file.infolist()
        for inner_file in file_list:
            file_name = inner_file.filename
            if file_name.endswith(".class"):
                package_set.add(".".join(file_name.split("/")[:-1]))
        jar_file.close()

    package_set |= set(irrelevant_packages["names"])

    with open(os.path.abspath(irrelevant_packages["libs"]), "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        first_row = next(csv_reader)
        for row in csv_reader:
            package_fields = row[0][len("L"):].split("/")
            if len(package_fields) > 1 and min([len(x) for x in package_fields]) > 1:
                package_set.add(".".join(package_fields))

    return package_set

def clean_stack_trace(stack_trace_set, ex_package_set):
    ret_stack_trace_set = set()
    for stack_trace in stack_trace_set:
        trimmed_stack_trace = stack_trace.split("$")[0]
        stack_trace_segments = trimmed_stack_trace.split(".")
        stack_trace_removed = False

        for idx, stack_trace_segment in enumerate(stack_trace_segments):
            if ".".join(stack_trace_segments[:idx + 1]) in ex_package_set:
                stack_trace_removed = True
                break

        if not stack_trace_removed:
            ret_stack_trace_set.add(stack_trace)

    return ret_stack_trace_set
