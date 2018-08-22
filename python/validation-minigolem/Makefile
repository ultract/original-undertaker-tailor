# Comments should be ignored

# Multi-line statements are interpreted as one line
obj-y := a.o \
		 b.o

obj-$(CONFIG_XY) += c.o	# Also, comments after the text should be ignored

ifeq ($(CONFIG_XY),)
    obj-y += d.o
else
    obj-y += e.o
endif

ifdef CONFIG_XY
    ifeq ($(CONFIG_XY),)
        obj-y += f.o
    else
        obj-y += g.o
	endif
else
    obj-y += h.o
endif

ifdef CONFIG_ABC
	obj-y += i.o
	ifeq ($(CONFIG_XY), y)
		obj-y += j.o
	else
		obj-y += k.o
	endif
else
	ifeq (${X86},)
		obj-y += l.o
	endif
	obj-y += m.o
endif

obj-$(CONFIG_DE) += xyz.o
ifeq ($(CONFIG_XY),)
	ifdef CONFIG_Z
		obj-y += z.o
	endif
	xyz-y := x.o
else
	xyz-$(CONFIG_Z) := y.o
endif
xyz-y += z.o

obj-$(CONFIG_DE) += subdir/

ifeq ($(some_dynamic_data_which_cannot_be_parsed),y)
	obj-y += never_present.o
endif
