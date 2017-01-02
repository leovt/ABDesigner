'''
Created on 13 Dec 2016

@author: leonhard
'''

import tkinter
import tkinter.filedialog
import array
from functools import partial
import json

BLACK = 0
WHITE = 1
TRANSPARENT = 2

class BitmapGrid(tkinter.Canvas):
    def __init__(self, master, callback=None, width=128, height=64):
        tkinter.Canvas.__init__(self, master, width=width * 8 - 1, height=height * 8 - 1)
        self._width = width
        self._height = height
        self._callback = callback

        self.shown = {}

        for i in range(self._height):
            for j in range(self._width):
                self.shown[i, j] = 'lightgrey'
                self.create_rectangle((j * 8, i * 8, j * 8 + 8, i * 8 + 8),
                                      fill='lightgrey',
                                      outline='grey',
                                      tags=('r%dc%s' % (i, j),))
                
        if callback:
            self.bind('<Button-1>', lambda event: callback(event.widget, event.y // 8, event.x // 8))

    def set_px(self, i, j, color):
        if self.shown[i, j] != color:
            self.itemconfigure('r%dc%s' % (i, j), fill=color)
            self.shown[i, j] = color

class Bitmap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.data = array.array('B', [TRANSPARENT] * (width * height))
        self.callbacks = []

    def set_px(self, i, j, color):
        self.data[i * self.width + j] = color
        
    def get_px(self, i, j):
        return self.data[i * self.width + j]

    def toggle_px(self, i, j):
        self.data[i * self.width + j] = (self.data[i * self.width + j] + 1) % 3

    def as_dict(self):
        pixels = []
        mask = []
        for i in range(0, self.height, 8):
            for j in range(self.width):
                p = 0
                m = 0
                for k in range(min(8, self.height - i)):
                    P = bool(self.get_px(i + k, j) & 1)
                    M = bool(self.get_px(i + k, j) & 2)
                    if M:
                        assert not P, (i, j, k, M, P)
                    if P:
                        p += 2 ** k
                    if M:
                        m += 2 ** k
                pixels.append(p)
                mask.append(m)

        return {'w': self.width, 'h': self.height,
                'image': pixels,
                'mask': mask}

    @classmethod
    def from_dict(cls, d):
        self = cls(d['w'], d['h'])
        pixels = iter(d['image'])
        mask = iter(d['mask'])
        for i in range(0, self.height, 8):
            for j in range(self.width):
                p = next(pixels)
                m = next(mask)
                # print(i, j, p, m, bin(p), bin(m))
                for k in range(min(8, self.height - i)):
                    M = bool(m & (2 ** k))
                    P = bool(p & (2 ** k))
                    if M:
                        assert not P, (i, j, k, M, P)
                    # print('   ', i + k, j, M, P)
                    self.set_px(i + k, j, P + 2 * M)
        return self

class Layer:
    def __init__(self, name, i, j, bm, visible):
        self.name = name
        self.i = i
        self.j = j
        self.bm = bm
        self.visible = visible

    def as_dict(self):
        return {
            'name': self.name,
            'i': self.i,
            'j': self.j,
            'visible': bool(self.visible),
            'bm': self.bm.as_dict()}

    @classmethod
    def from_dict(cls, d):
        return cls(d['name'], d['i'], d['j'], Bitmap.from_dict(d['bm']), d['visible'])


class Document:
    def __init__(self):
        self.layers = [Layer('background', 0, 0, Bitmap(128, 64), True),
                       Layer('sp1', 10, 20, Bitmap(16, 16), True)]

    def as_dict(self):
        return {
            'layers': [layer.as_dict() for layer in self.layers]}

    @classmethod
    def from_dict(cls, d):
        self = cls()
        self.layers[:] = [Layer.from_dict(ld) for ld in d['layers']]
        return self

    def get_px(self, i, j):
        px = TRANSPARENT
        for layer in self.layers:
            if (layer.visible and
                layer.i <= i < layer.i + layer.bm.height and
                layer.j <= j < layer.j + layer.bm.width):
                px = {BLACK:BLACK, WHITE:WHITE, TRANSPARENT:px}[layer.bm.get_px(i - layer.i, j - layer.j)]
        return px

class Editor:
    def __init__(self, master):
        self.grid = BitmapGrid(master, self.modify)
        self.layer_frame = tkinter.Frame(master, relief='sunken', border=2, bg='white')
        self.grid.grid(row=0, column=0, sticky='nswe')
        self.layer_frame.grid(row=0, column=1, sticky='nswe')
        self.edit = tkinter.IntVar(self.layer_frame, value=0)
        self.edit.trace('w', self.toggle_edit)
        self.ed_layer = self.grid.create_rectangle((-1, -1, 0, 0), outline='red')
        self.layer_btns = []
        self.document = None
        self.new()

    def new(self):
        self.document = Document()
        self.load_doc()

    def open(self):
        fname = tkinter.filedialog.askopenfilename()
        if not fname:
            return
        with open(fname, 'r') as f:
            self.document = Document.from_dict(json.load(f))
        self.load_doc()

    def save(self):
        fname = tkinter.filedialog.asksaveasfilename()
        if not fname:
            return
        with open(fname, 'w') as f:
            json.dump(self.document.as_dict(), f)

    def load_doc(self):
        for btn in self.layer_btns:
            btn.destroy()

        for row, layer in enumerate(self.document.layers):
            vis = tkinter.IntVar(self.layer_frame, value=1)
            cb = tkinter.Checkbutton(self.layer_frame, text='', bg='white', border=0, var=vis)
            cb.grid(row=row, column=0)
            rb = tkinter.Radiobutton(self.layer_frame,
                                text=layer.name,
                                bg='white',
                                border=0,
                                variable=self.edit,
                                value=row)
            rb.grid(row=row, column=1, sticky='w')
            self.layer_btns.append(cb)
            self.layer_btns.append(rb)
            vis.trace('w', partial(self.toggle_visibility, layer, vis))
        self.redraw()

    def toggle_visibility(self, layer, var, *args):
        layer.visible = not layer.visible
        self.redraw()
    
    def toggle_edit(self, *args):
        layer = self.document.layers[self.edit.get()]
        self.grid.coords(self.ed_layer, (layer.j * 8, layer.i * 8, (layer.j + layer.bm.width) * 8, (layer.i + layer.bm.height) * 8))
        self.redraw()

    def modify(self, grid, i, j):
        layer = self.document.layers[self.edit.get()]
        if (layer.visible and
            layer.i <= i < layer.i + layer.bm.height and
            layer.j <= j < layer.j + layer.bm.width):
            layer.bm.toggle_px(i-layer.i, j-layer.j)
            self.redraw_px(i, j)

    def redraw_px(self, i, j):
        px = self.document.get_px(i, j)
        layer = self.document.layers[self.edit.get()]
        if (layer.visible and
            layer.i <= i < layer.i + layer.bm.height and
            layer.j <= j < layer.j + layer.bm.width):
            px2 = layer.bm.get_px(i - layer.i, j - layer.j)
            color = {(BLACK, BLACK): 'black',
                     (WHITE, WHITE): 'white',
                     (TRANSPARENT, TRANSPARENT): 'lightgrey',
                     (BLACK, TRANSPARENT): '#704040',
                     (WHITE, TRANSPARENT): '#F0C0C0',
                     (BLACK, WHITE): 'red',
                     (WHITE, BLACK): 'red'}[px, px2]
        else:
            color = {BLACK: 'black',
                     WHITE: 'white',
                     TRANSPARENT: 'lightgrey'}[px]
        self.grid.set_px(i, j, color)

    def redraw(self):
        for i in range(64):
            for j in range(128):
                self.redraw_px(i, j)


def main():
    tk = tkinter.Tk()
    ed = Editor(tk)
    menu = tkinter.Menu(tk)
    fmenu = tkinter.Menu(tk)
    fmenu.add_command(label='New', command=ed.new)
    fmenu.add_command(label='Open ...', command=ed.open)
    fmenu.add_command(label='Save As ...', command=ed.save)
    menu.add_cascade(label='File', menu=fmenu)
    tk.config(menu=menu)
    tk.mainloop()

if __name__ == '__main__':
    main()
