# SPDX-License-Identifier: MIT
# Copyright (c) 2021 patgolez10, hbens

# type: ignore

import ast

__all__ = [
    'gen_assign_name_checker_ast',
    'gen_assign_generic_checker_ast',
    'AssignTransformer'
]

try:
    import astor   # convert ast to python for debug
    dump_tree = astor.to_source
except ImportError:
    dump_tree = ast.dump

debug = False


# return a best guess for a rhs name
def node_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id
    return None


def as_store(n):
    if debug:
        print('as_store n=', ast.dump(n))

    new_n = n
    if isinstance(n, ast.Name):
        new_n = ast.Name(id=n.id, ctx=ast.Store())

    elif isinstance(n, ast.Attribute):
        # Attribute(value=Name(id='self', ctx=Load()), attr='name', ctx=Store())
        if isinstance(n.ctx, ast.Load):
            v = n.value
            if isinstance(v, ast.Name):
                new_n = ast.Attribute(
                        value=ast.Name(id=v.id, ctx=ast.Load()),
                        attr=n.attr,
                        ctx=ast.Store())
    else:
        if debug:
            print("warning: as_store, don't know how to handle", ast.dump(n))

    if debug and (new_n is not n):
        print('as_store new_n=', ast.dump(new_n))
    return new_n


def as_load(n):
    if debug:
        print('as_load n=', ast.dump(n))

    new_n = n
    if isinstance(n, ast.Name):
        new_n = ast.Name(id=n.id, ctx=ast.Load())

    elif isinstance(n, ast.Attribute):
        # Attribute(value=Name(id='self', ctx=Load()), attr='name', ctx=Load())
        v = n.value
        if isinstance(v, ast.Name):
            new_n = ast.Attribute(
                    value=ast.Name(id=v.id, ctx=ast.Load()),
                    attr=n.attr,
                    ctx=ast.Load())
    else:
        if debug:
            print("warning: as_load, don't know how to handle", ast.dump(n))

    if debug and (new_n is not n):
        print('as_load new_n=', ast.dump(new_n))
    return new_n

def core_assign(node, lhs_target, rhs_obj_name):
    if isinstance(node, ast.Assign):
        return ast.Assign(
            targets=[as_store(lhs_target)],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=rhs_obj_name, ctx=ast.Load()),
                    attr='__assignpre__',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Constant(node_name(lhs_target)),  # lhs_name
                    ast.Constant(rhs_obj_name),           # rhs_name
                    node.value                            # rhs_value
                    ],
                keywords=[],
                starargs=None,
                kwargs=None
            )
        )
    elif isinstance(node, ast.AnnAssign):
        return ast.AnnAssign(
            targets=[as_store(lhs_target)],
            annotation=node.annotation,
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=rhs_obj_name, ctx=ast.Load()),
                    attr='__assignpre__',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Constant(node_name(lhs_target)),  # lhs_name
                    ast.Constant(rhs_obj_name),           # rhs_name
                    node.value                            # rhs_value
                    ],
                keywords=[],
                starargs=None,
                kwargs=None
            ),
            simple=node.simple
        )
    else:
        raise ValueError(f"core_assign, don't know how to handle {ast.dump(node)}")

def gen_assign_name_checker_ast(node):

    assert isinstance(node.value, ast.Name)

    if debug:
        print('old_node: x=y case')
        print(dump_tree(node))

    rhs_obj_name = node.value.id

    if isinstance(node, ast.Assign):
        node_targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        node_targets = [ node.target ]
    else:
        if debug:
            print("warning: gen_assign_name_checker_ast, don't know how to handle", ast.dump(node))
        return node

    new_node = ast.If(
        test=ast.Constant(value=True, kind=None),
        orelse=[],
        body=[
          ast.If(
            test=ast.Call(
                func=ast.Name(id='hasattr', ctx=ast.Load()),
                args=[
                    ast.Name(id=rhs_obj_name, ctx=ast.Load()),
                    ast.Constant('__assignpre__'),
                ],
                keywords=[],
                starargs=None,
                kwargs=None
            ),
            body=[
                core_assign(node, lhs_target, rhs_obj_name) for lhs_target in node_targets
            ],
            orelse=[node]
          ),
          ast.If(
            test=ast.Constant(value=True, kind=None),
            orelse=[],
            body=[
                ast.If(
                    test=ast.Call(
                        func=ast.Name(id='hasattr', ctx=ast.Load()),
                        args=[
                            as_load(lhs_target),
                            ast.Constant('__assignpost__'),
                        ],
                        keywords=[],
                        starargs=None,
                        kwargs=None
                    ),
                    body=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Attribute(
                                        value=as_load(lhs_target),
                                        attr='__assignpost__',
                                        ctx=ast.Load()),
                                args=[
                                    ast.Constant(node_name(lhs_target)),  # lhs_name
                                    ast.Constant(node_name(node.value))   # rhs_name
                                ],
                                keywords=[]
                            )
                        )
                    ],
                    orelse=[]
                )
            for lhs_target in node_targets]
          )
        ]
    )
    if debug:
        print('new_node:')
        print(dump_tree(new_node))
    return new_node


def gen_assign_generic_checker_ast(node):

    assert isinstance(node.value, (ast.BinOp, ast.Call, ast.UnaryOp))

    if isinstance(node, ast.Assign):
        node_targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        node_targets = [ node.target ]
    else:
        if debug:
            print("warning: gen_assign_name_checker_ast, don't know how to handle", ast.dump(node))
        return node

    for lhs_target in node_targets:
        if not isinstance(lhs_target, ast.Name) and not isinstance(lhs_target, ast.Tuple):
            if debug:
                print('old_node: generic case')
                print(dump_tree(node))
                print('do NOT know how to handle node')
            return node

    if debug:
        print('old_node: generic case')
        print(dump_tree(node))

    body = [node]
    for lhs_target in node_targets:
        if isinstance(lhs_target, ast.Name):
            body.append(
                ast.If(
                    test=ast.Call(
                        func=ast.Name(id='hasattr', ctx=ast.Load()),
                        args=[
                            as_load(lhs_target),
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
                                    value=as_load(lhs_target),
                                    attr='__assignpost__',
                                    ctx=ast.Load()),
                                args=[
                                    ast.Constant(lhs_target.id),         # lhs_name
                                    ast.Constant(node_name(node.value))  # rhs_name
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
                                        ast.Constant(node_name(node.value))  # rhs_name
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
    if debug:
        print('new_node:')
        print(dump_tree(new_node))
    return new_node


def gen_assign_dispatch(node):
    new_node = None
    if isinstance(node.value, ast.Name):
        new_node = gen_assign_name_checker_ast(node)
    elif isinstance(node.value, (ast.BinOp, ast.Call, ast.UnaryOp)):
        new_node = gen_assign_generic_checker_ast(node)

    if new_node is not None:
        ast.copy_location(new_node, node)
        ast.fix_missing_locations(new_node)
        return new_node

    return node

class AssignTransformer(ast.NodeTransformer):
    def generic_visit(self, node):
        ast.NodeTransformer.generic_visit(self, node)
        return node

    def visit_Assign(self, node):
        return gen_assign_dispatch(node)

    def visit_AnnAssign(self, node):
        if not hasattr(node, "value"):
            return node # Annotation only
        return gen_assign_dispatch(node)
