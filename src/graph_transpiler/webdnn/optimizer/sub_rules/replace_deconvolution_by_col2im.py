from typing import Tuple

from webdnn.graph import traverse
from webdnn.graph.axis import Axis
from webdnn.graph.graph import Graph
from webdnn.graph.operators.col2im import Col2Im
from webdnn.graph.operators.deconvolution2d import Deconvolution2D
from webdnn.graph.operators.sgemm import Sgemm
from webdnn.graph.optimize_rule import OptimizeRule
from webdnn.graph.order import OrderNHWC, OrderCHWN


class ReplaceDeconvolutionByCol2Im(OptimizeRule):
    """
    Replace Deconvolution2D by SGEMM and Col2Im
    """

    def optimize(self, graph: Graph) -> Tuple[Graph, bool]:
        flag_changed = False
        for op in traverse.filter_nodes(traverse.listup_operators(graph), Deconvolution2D):  # type: Deconvolution2D
            x = op.inputs["x"]
            w = op.inputs["w"]
            y = op.outputs["y"]

            flag_changed = True
            op.remove_all()

            x = x.transpose(OrderNHWC)
            w = w.transpose(OrderCHWN)

            col, = Sgemm(None,
                         M=x.shape_dict[Axis.N] * x.shape_dict[Axis.H] * x.shape_dict[Axis.W],
                         N=w.shape_dict[Axis.H] * w.shape_dict[Axis.W] * w.shape_dict[Axis.N],
                         K=x.shape_dict[Axis.C],
                         out_shape=[x.shape_dict[Axis.N],
                                    x.shape_dict[Axis.H],
                                    x.shape_dict[Axis.W],
                                    w.shape_dict[Axis.H] * w.shape_dict[Axis.W] * w.shape_dict[Axis.N]],
                         out_order=OrderNHWC,
                         transpose_A=True,
                         transpose_B=True)(x, w)

            new_y, = Col2Im(None, ksize=op.ksize, stride=op.stride, padding=op.padding)(col)
            OptimizeRule.replace_variable(graph, new_y.transpose_like(y), y)

        return graph, flag_changed
