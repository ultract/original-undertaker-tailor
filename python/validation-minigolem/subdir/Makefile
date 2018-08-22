obj-$(CONFIG_DE) := s123.o

ifdef CONFIG_XY
    s123-y += s1.o
else
    s123-$(CONFIG_Z) += s2.o
endif

s123-y += s3.o

#Testcase for nested macros
list-$(CONFIG_Z) += s4.o
s123-$(CONFIG_FG) += $(list-y)

#Testcase for $(subst m,y,$(CONFIG_BLA)) and $(CONFIG_BLA:m=y)
obj-$(subst m,y,$(CONFIG_Z)) += s5.o
obj-$(CONFIG_Z:m=y) += s6.o
