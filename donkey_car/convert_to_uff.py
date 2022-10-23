#!/usr/bin/env python3
# Copyright 1993-2020 NVIDIA Corporation.  All rights reserved.
#
# NOTICE TO LICENSEE:
#
# This source code and/or documentation ("Licensed Deliverables") are
# subject to NVIDIA intellectual property rights under U.S. and
# international Copyright laws.
#
# These Licensed Deliverables contained herein is PROPRIETARY and
# CONFIDENTIAL to NVIDIA and is being provided under the terms and
# conditions of a form of NVIDIA software license agreement by and
# between NVIDIA and Licensee ("License Agreement") or electronically
# accepted by Licensee.  Notwithstanding any terms or conditions to
# the contrary in the License Agreement, reproduction or disclosure
# of the Licensed Deliverables to any third party without the express
# written consent of NVIDIA is prohibited.
#
# NOTWITHSTANDING ANY TERMS OR CONDITIONS TO THE CONTRARY IN THE
# LICENSE AGREEMENT, NVIDIA MAKES NO REPRESENTATION ABOUT THE
# SUITABILITY OF THESE LICENSED DELIVERABLES FOR ANY PURPOSE.  IT IS
# PROVIDED "AS IS" WITHOUT EXPRESS OR IMPLIED WARRANTY OF ANY KIND.
# NVIDIA DISCLAIMS ALL WARRANTIES WITH REGARD TO THESE LICENSED
# DELIVERABLES, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY,
# NONINFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
# NOTWITHSTANDING ANY TERMS OR CONDITIONS TO THE CONTRARY IN THE
# LICENSE AGREEMENT, IN NO EVENT SHALL NVIDIA BE LIABLE FOR ANY
# SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THESE LICENSED DELIVERABLES.
#
# U.S. Government End Users.  These Licensed Deliverables are a
# "commercial item" as that term is defined at 48 C.F.R. 2.101 (OCT
# 1995), consisting of "commercial computer software" and "commercial
# computer software documentation" as such terms are used in 48
# C.F.R. 12.212 (SEPT 1995) and is provided to the U.S. Government
# only as a commercial end item.  Consistent with 48 C.F.R.12.212 and
# 48 C.F.R. 227.7202-1 through 227.7202-4 (JUNE 1995), all
# U.S. Government End Users acquire the Licensed Deliverables with
# only those rights set forth herein.
#
# Any use of the Licensed Deliverables in individual and commercial
# software must include, in the user documentation and internal
# comments to the code, the above Disclaimer and U.S. Government End
# Users Notice.

"""
convert_to_uff.py

Main script for doing uff conversions from
different frameworks.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
# Make sure we import the correct UFF
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
import argparse

# import uff
# import tf_converters as uff
# from tf_converters.conversion_helpers import from_tensorflow_frozen_model

try:
    from tensorflow.python.platform import gfile
    import tensorflow as tf
    from tensorflow.compat.v1 import GraphDef
except ImportError as err:
    raise ImportError("""ERROR: Failed to import module ({})
Please make sure you have TensorFlow installed.
For installation instructions, see:
https://www.tensorflow.org/install/""".format(err))

import numpy as np
import uff
import uff.model
import os

def _replace_ext(path, ext):
    return os.path.splitext(path)[0] + ext

def from_tensorflow(graphdef, output_nodes=[], preprocessor=None, **kwargs):
    """
    Converts a TensorFlow GraphDef to a UFF model.

    Args:
        graphdef (tensorflow.GraphDef): The TensorFlow graph to convert.
        output_nodes (list(str)): The names of the outputs of the graph. If not provided, graphsurgeon is used to automatically deduce output nodes.
        output_filename (str): The UFF file to write.
        preprocessor (str): The path to a preprocessing script that will be executed before the converter. This script should define a ``preprocess`` function which accepts a graphsurgeon DynamicGraph and modifies it in place.
        write_preprocessed (bool): If set to True, the converter will write out the preprocessed graph as well as a TensorBoard visualization. Must be used in conjunction with output_filename.
        text (bool): If set to True, the converter will also write out a human readable UFF file. Must be used in conjunction with output_filename.
        quiet (bool): If set to True, suppresses informational messages. Errors may still be printed.
        debug_mode (bool): If set to True, the converter prints verbose debug messages.
        return_graph_info (bool): If set to True, this function returns the graph input and output nodes in addition to the serialized UFF graph.

    Returns:
        serialized UFF MetaGraph (str)

        OR, if return_graph_info is set to True,

        serialized UFF MetaGraph (str), graph inputs (list(tensorflow.NodeDef)), graph outputs (list(tensorflow.NodeDef))
    """

    quiet = False
    input_node = []
    text = False
    list_nodes = False
    output_filename = None
    write_preprocessed = False
    debug_mode = False
    return_graph_info = False
    for k, v in kwargs.items():
        if k == "quiet":
            quiet = v
        elif k == "input_node":
            input_node = v
        elif k == "text":
            text = v
        elif k == "list_nodes":
            list_nodes = v
        elif k == "output_filename":
            output_filename = v
        elif k == "write_preprocessed":
            write_preprocessed = v
        elif k == "debug_mode":
            debug_mode = v
        elif k == "return_graph_info":
            return_graph_info = v

    tf_supported_ver = "1.15.0"
    if tf.__version__ != tf_supported_ver:
        print("NOTE: UFF has been tested with TensorFlow " + str(tf_supported_ver) + ".")
        print("WARNING: The version of TensorFlow installed on this system is not guaranteed to work with UFF.")

    try:
        import graphsurgeon as gs
    except ImportError as err:
        raise ImportError("""ERROR: Failed to import module ({})
Please make sure you have graphsurgeon installed.
For installation instructions, see:
https://docs.nvidia.com/deeplearning/sdk/tensorrt-api/#python and click on the 'TensoRT Python API' link""".format(err))
    # Create a dynamic graph so we can adjust it as needed.
    dynamic_graph = gs.DynamicGraph(graphdef)
    # Always remove assert ops.
    assert_nodes = dynamic_graph.find_nodes_by_op("Assert")
    dynamic_graph.remove(assert_nodes, remove_exclusive_dependencies=True)
    # Now, run the preprocessor, if provided.
    if preprocessor:
        import importlib, sys
        # Temporarily insert this working dir into the sys.path
        sys.path.insert(0, os.path.dirname(preprocessor))
        # Import and execute!
        pre = importlib.import_module(os.path.splitext(os.path.basename(preprocessor))[0])
        pre.preprocess(dynamic_graph)
        # Now clean up, by removing the directory from the system path.
        del sys.path[0]
    # Run process_dilated_conv() and process_softmax() so the user doesn't have to.
    gs.extras.process_dilated_conv(dynamic_graph)
    gs.extras.process_softmax(dynamic_graph)

    # Get the modified graphdef back.
    graphdef = dynamic_graph.as_graph_def()

    if write_preprocessed and output_filename:
        preprocessed_output_name = os.path.splitext(output_filename)[0] + "_preprocessed"
        dynamic_graph.write(preprocessed_output_name + ".pb")
        dynamic_graph.write_tensorboard(preprocessed_output_name)
        if not quiet:
            print("Preprocessed graph written to " + preprocessed_output_name + ".pb")
            print("TensorBoard visualization written to " + preprocessed_output_name)

    if not quiet:
        print("UFF Version " + uff.__version__)
        if debug_mode:
            _debug_print("Debug Mode is ENABLED")

    if not input_node:
        if not quiet:
            print("=== Automatically deduced input nodes ===")
            print(str(dynamic_graph.graph_inputs))
            print("=========================================\n")
    # Deduce the likely graph outputs if none are provided
    if not output_nodes:
        output_nodes = [node.name for node in dynamic_graph.graph_outputs]
        if not quiet:
            print("=== Automatically deduced output nodes ===")
            print(str(dynamic_graph.graph_outputs))
            print("==========================================\n")

    if list_nodes:
        for i, node in enumerate(graphdef.node):
            print('%i %s: "%s"' % (i + 1, node.op, node.name))
        return

    for i, name in enumerate(output_nodes):
        if debug_mode:
            _debug_print("Enumerating outputs")
        output_nodes[i] = tf2uff.convert_node_name_or_index_to_name(
            name, graphdef.node, debug_mode=debug_mode)
        if not quiet:
            print("Using output node", output_nodes[i])

    input_replacements = {}
    for i, name_data in enumerate(input_node):
        name, new_name, dtype, shape = name_data.split(',', 3)
        name = tf2uff.convert_node_name_or_index_to_name(name, graphdef.node, debug_mode=debug_mode)
        if new_name == '':
            new_name = name
        dtype = np.dtype(dtype)
        shape = [int(x) for x in shape.split(',')]
        input_replacements[name] = (new_name, dtype, shape)
        if not quiet:
            print("Using input node", name)

    if not quiet:
        print("Converting to UFF graph")

    uff_metagraph = uff.model.MetaGraph()
    tf2uff.add_custom_descriptors(uff_metagraph)
    uff_graph = tf2uff.convert_tf2uff_graph(
        graphdef,
        uff_metagraph,
        output_nodes=output_nodes,
        input_replacements=input_replacements,
        name="main",
        debug_mode=debug_mode)

    uff_metagraph_proto = uff_metagraph.to_uff()
    if not quiet:
        print('No. nodes:', len(uff_graph.nodes))

    if output_filename:
        with open(output_filename, 'wb') as f:
            f.write(uff_metagraph_proto.SerializeToString())
        if not quiet:
            print("UFF Output written to", output_filename)
        if text:  # ASK: Would you want to return the prototxt?
            if not output_filename:
                raise ValueError(
                    "Requested prototxt but did not provide file path")
            output_filename_txt = _replace_ext(output_filename, '.pbtxt')
            with open(output_filename_txt, 'w') as f:
                f.write(str(uff_metagraph.to_uff(debug=True)))
            if not quiet:
                print("UFF Text Output written to", output_filename_txt)
    # Always return the UFF graph!
    if return_graph_info:
        return uff_metagraph_proto.SerializeToString(), dynamic_graph.graph_inputs, dynamic_graph.graph_outputs
    else:
        return uff_metagraph_proto.SerializeToString()

def from_tensorflow_frozen_model(frozen_file, output_nodes=[], preprocessor=None, **kwargs):
    """
    Converts a TensorFlow frozen graph to a UFF model.

    Args:
        frozen_file (str): The path to the frozen TensorFlow graph to convert.
        output_nodes (list(str)): The names of the outputs of the graph. If not provided, graphsurgeon is used to automatically deduce output nodes.
        output_filename (str): The UFF file to write.
        preprocessor (str): The path to a preprocessing script that will be executed before the converter. This script should define a ``preprocess`` function which accepts a graphsurgeon DynamicGraph and modifies it in place.
        write_preprocessed (bool): If set to True, the converter will write out the preprocessed graph as well as a TensorBoard visualization. Must be used in conjunction with output_filename.
        text (bool): If set to True, the converter will also write out a human readable UFF file. Must be used in conjunction with output_filename.
        quiet (bool): If set to True, suppresses informational messages. Errors may still be printed.
        debug_mode (bool): If set to True, the converter prints verbose debug messages.
        return_graph_info (bool): If set to True, this function returns the graph input and output nodes in addition to the serialized UFF graph.

    Returns:
        serialized UFF MetaGraph (str)

        OR, if return_graph_info is set to True,

        serialized UFF MetaGraph (str), graph inputs (list(tensorflow.NodeDef)), graph outputs (list(tensorflow.NodeDef))
    """
    graphdef = GraphDef()
    #with tf.gfile.GFile(frozen_file, "rb") as frozen_pb:
    with tf.io.gfile.GFile(frozen_file, "rb") as frozen_pb:
        graphdef.ParseFromString(frozen_pb.read())
    return from_tensorflow(graphdef, output_nodes, preprocessor, **kwargs)



def _replace_ext(path, ext):
    return os.path.splitext(path)[0] + ext

def process_cmdline_args():
    """
    Helper function for processing commandline arguments
    """
    parser = argparse.ArgumentParser(description="""Converts TensorFlow models to Unified Framework Format (UFF).""")

    parser.add_argument(
        "input_file",
        help="""path to input model (protobuf file of frozen GraphDef)""")

    parser.add_argument(
        '-l', '--list-nodes', action='store_true',
        help="""show list of nodes contained in input file""")

    parser.add_argument(
        '-t', '--text', action='store_true',
        help="""write a text version of the output in addition to the
        binary""")

    parser.add_argument(
        '--write_preprocessed', action='store_true',
        help="""write the preprocessed protobuf in addition to the
        binary""")

    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help="""disable log messages""")

    parser.add_argument(
        '-d', '--debug', action='store_true',
        help="""Enables debug mode to provide helpful debugging output""")

    parser.add_argument(
        "-o", "--output",
        help="""name of output uff file""")

    parser.add_argument(
        "-O", "--output-node", default=[], action='append',
        help="""name of output nodes of the model""")

    parser.add_argument(
        '-I', '--input-node', default=[], action='append',
        help="""name of a node to replace with an input to the model.
        Must be specified as: "name,new_name,dtype,dim1,dim2,..."
        """)

    parser.add_argument(
        "-p", "--preprocessor",
        help="""the preprocessing file to run before handling the graph. This file must define a `preprocess` function that accepts a GraphSurgeon DynamicGraph as it's input. All transformations should happen in place on the graph, as return values are discarded""")

    args, _ = parser.parse_known_args()
    args.output = _replace_ext((args.output if args.output else args.input_file), ".uff")
    return args, _

def main():
    args, _ = process_cmdline_args()
    if not args.quiet:
        print("Loading", args.input_file)
    # uff.from_tensorflow_frozen_model(
    from_tensorflow_frozen_model(
        args.input_file,
        output_nodes=args.output_node,
        preprocessor=args.preprocessor,
        input_node=args.input_node,
        quiet=args.quiet,
        text=args.text,
        list_nodes=args.list_nodes,
        output_filename=args.output,
        write_preprocessed=args.write_preprocessed,
        debug_mode=args.debug
    )

if __name__ == '__main__':
    main()
