from ast import arg


def worker_calc_weight_grd(args):
    unique_name, pyscissor_obj = args
    weight_grid = pyscissor_obj.get_masked_weight_recursive()
    return {'uid': unique_name, 'wg': weight_grid}


def worker_ens_pr_cp_sum(args):
    quant, cp, lsp = args

    tp = (cp[:] + lsp[:]) * 1000

    return {
        'q': quant,
        'tp': tp
    }
