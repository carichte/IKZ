def imshow(ax, data, alpha, **imshow_kw):
    """
        Adds a transparent image to the figure axes `ax`.
    """
    im = ax.imshow(data, **imshow_kw)
    vmin, vmax = im.get_clim()
    cmap = im.get_cmap()
    norm = im.norm
    im.set_visible(False)

    value = norm(data, clip=True)#(data)
    rgba  = cmap(value)
    rgba[:,:,-1] = alpha

    ax.imshow(rgba, **imshow_kw)
    return im






if __name__ == "__main__":
    import pylab as pl
    from scipy import ndimage

    data = pl.rand(51, 51) * 5
    alpha = pl.zeros((51, 51))
    alpha[25,25] = 1.
    alpha = ndimage.gaussian_filter(alpha, 10)

    alpha/= alpha.max()


    fig, ax = pl.subplots(1, 1)
    im = imshow(ax, data, alpha, interpolation="nearest", origin="lower")

    cb = pl.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Colorbar")
    ax.set_xlabel('pix (um)')
    ax.set_ylabel('piy (um)')
    ax.axis('tight')
    ax.set_aspect('equal', adjustable="box-forced")
    pl.tight_layout()
    pl.show()

