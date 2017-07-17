def java_method_convert(short_sig):
    basic_type_mapping = {
        "Z": "boolean",
        "B": "byte",
        "C": "char",
        "S": "short",
        "I": "int",
        "J": "long",
        "F": "float",
        "D": "double"
    }
    fields = short_sig.split()
    idx = 1
    array_depth = 0
    parsed_paras = []
    while fields[1][idx] != ")":
        if fields[1][idx] == "L":
            class_end_idx = idx
            while fields[1][class_end_idx] != ";":
                class_end_idx += 1
            parsed_paras.append(fields[1][idx + 1:class_end_idx].replace("/", ".") + array_depth * "[]")
            idx = class_end_idx
        elif fields[1][idx] == "[":
            array_depth += 1
        else:
            parsed_paras.append(basic_type_mapping[fields[1][idx]] + array_depth * "[]")
            array_depth = 0
        idx += 1
    return "%s(%s)" % (fields[0], ",".join(parsed_paras))


def get_monitoring_methods(trace_item_list):
    ret_list = []
    method_filter = set([")Z", ")B", ")C", ")S", ")I", ")J"])

    for trace_item in trace_item_list:
        fields = trace_item.split()
        sig_end = fields[1][-len(")X"):]
        if sig_end in method_filter:
            ret_list.append(java_method_convert(trace_item))
    return set(ret_list)

def extract_method_classes(methods_list):
    return sorted(list(set([
        ".".join(x.split("(")[0].split(".")[:-1]) for x in methods_list
    ])))
