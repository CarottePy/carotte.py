# SPDX-License-Identifier: MIT
# Copyright (c) 2021 patgolez10, hbens

'''assignhooks patch'''

import ast

import assignhooks  # type: ignore


def gen_assign_checker_ast(node): # type: ignore
    '''assignhooks patch to handle more cases'''

    assert isinstance(node.value, (ast.BinOp, ast.Call, ast.UnaryOp))

    for lhs_target in node.targets:
        if not isinstance(lhs_target, ast.Name) and not isinstance(lhs_target, ast.Tuple):
            if assignhooks.transformer.debug:
                print('old_node: generic case')
                print(assignhooks.transformer.dump_tree(node))
                print('do NOT know how to handle node')
            return node

    if assignhooks.transformer.debug:
        print('old_node: generic case')
        print(assignhooks.transformer.dump_tree(node))

    body = [node]
    for lhs_target in node.targets:
        if isinstance(lhs_target, ast.Name):
            body.append(
                ast.If(
                    test=ast.Call(
                        func=ast.Name(id='hasattr', ctx=ast.Load()),
                        args=[
                            assignhooks.transformer.as_load(lhs_target),
                            ast.Constant('__assignpost__'),
                        ],
                        keywords=[],
                        starargs=None,
                        kwargs=None
                    ),
                    orelse=[],
                    body=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                    value=assignhooks.transformer.as_load(lhs_target),
                                    attr='__assignpost__',
                                    ctx=ast.Load()),
                                args=[
                                    ast.Constant(lhs_target.id),         # lhs_name
                                    ast.Constant(assignhooks.transformer.node_name(node.value))  # rhs_name
                                ],
                                keywords=[]
                            )
                        )
                        ]
                )
            )
        elif isinstance(lhs_target, ast.Tuple):
            for var in lhs_target.elts:
                body.append(
                    ast.If(
                        test=ast.Call(
                            func=ast.Name(id='hasattr', ctx=ast.Load()),
                            args=[
                                ast.Name(id=var.id, ctx=ast.Load()),
                                ast.Constant('__assignpost__'),
                            ],
                            keywords=[],
                            starargs=None,
                            kwargs=None
                        ),
                        orelse=[],
                        body=[
                            ast.Expr(
                                value=ast.Call(
                                    func=ast.Attribute(
                                        value=ast.Name(id=var.id, ctx=ast.Load()),
                                        attr='__assignpost__',
                                        ctx=ast.Load()),
                                    args=[
                                        ast.Constant(var.id),         # lhs_name
                                        ast.Constant(assignhooks.transformer.node_name(node.value))  # rhs_name
                                    ],
                                    keywords=[]
                                )
                            )
                        ]
                    )
                )

    new_node = ast.If(
        test=ast.Constant(value=True, kind=None),
        orelse=[],
        body=body
    )
    if assignhooks.transformer.debug:
        print('new_node:')
        print(assignhooks.transformer.dump_tree(new_node))
    return new_node

def visit_Assign(self, node): # type: ignore # pylint: disable=W0613
    '''assignhooks patch to handle more cases'''

    new_node = None
    if isinstance(node.value, ast.Name):
        new_node = assignhooks.transformer.gen_assign_name_checker_ast(node)
    elif isinstance(node.value, (ast.BinOp, ast.Call, ast.UnaryOp)):
        new_node = gen_assign_checker_ast(node)

    if new_node is not None:
        ast.copy_location(new_node, node)
        ast.fix_missing_locations(new_node)
        return new_node

    return node
