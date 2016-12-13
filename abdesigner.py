'''
Created on 13 Dec 2016

@author: leonhard
'''

import tkinter
import random
import array
from functools import partial

class BitmapGrid(tkinter.Canvas):
    def __init__(self, master, callback=None, width=128, height=64):
        tkinter.Canvas.__init__(self, master, width=width * 8 - 1, height=height * 8 - 1, bg='yellow')
        self._width = width
        self._height = height
        self._callback = callback

        for i in range(self._height):
            for j in range(self._width):
                self.create_rectangle((j * 8, i * 8, j * 8 + 8, i * 8 + 8),
                                      fill='white',
                                      outline='grey',
                                      tags=('r%dc%s' % (i, j),))
                
        if callback:
            self.bind('<Button-1>', lambda event: callback(event.widget, event.y // 8, event.x // 8))

    def set_px(self, i, j, color):
        self.itemconfigure('r%dc%s' % (i, j), fill=color)

class Bitmap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.data = array.array('B', [0] * (width * height))
        self.callbacks = []

    def set_px(self, i, j, color):
        self.data[i * self.width + j] = color
        
    def get_px(self, i, j):
        return self.data[i * self.width + j]


class Layer:
    def __init__(self, name, i, j, bm, visible):
        self.name = name
        self.i = i
        self.j = j
        self.bm = bm
        self.visible = visible

class Document:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.layers = [Layer('background', 0, 0, Bitmap(width, height), True),
                       Layer('sp1', 10, 20, Bitmap(16, 16), True)]

class Editor:
    def __init__(self, master, document):
        self.grid = BitmapGrid(master, self.modify)
        self.layer_frame = tkinter.Frame(master, relief='sunken', border=2, bg='white')
        self.grid.grid(row=0, column=0, sticky='nswe')
        self.layer_frame.grid(row=0, column=1, sticky='nswe')
        self.document = document
        self.edit = tkinter.IntVar(self.layer_frame, value=0)
        self.edit.trace('w', self.toggle_edit)
        
        for row, layer in enumerate(self.document.layers):
            vis = tkinter.IntVar(self.layer_frame, value=1)
            tkinter.Checkbutton(self.layer_frame, text='', bg='white', border=0, var=vis
                                ).grid(row=row, column=0)
            tkinter.Radiobutton(self.layer_frame,
                                text=layer.name,
                                bg='white',
                                border=0,
                                variable=self.edit,
                                value=row
                                ).grid(row=row, column=1, sticky='w')
            vis.trace('w', partial(self.toggle_visibility, layer, vis))

    def toggle_visibility(self, layer, var, *args):
        print('vis', layer.name, var.get())
    
    def toggle_edit(self, *args):
        layer = self.document.layers[self.edit.get()]
        print('edit', layer.name)

    def modify(self, grid, i, j):
        grid.set_px(i, j, random.choice(['red', 'green', 'blue']))

def main():
    tk = tkinter.Tk()
    ed = Editor(tk, Document(128, 64))
    tk.mainloop()

if __name__ == '__main__':
    main()
