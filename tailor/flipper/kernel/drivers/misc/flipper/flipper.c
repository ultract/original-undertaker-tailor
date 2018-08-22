/*
 * Flipper tailor - bit field implementation
 *
 * Copyright (C) 2014 Bernhard Heinloth <bernhard@heinloth.net>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 2 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307, USA.
 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <asm/uaccess.h>
#include <linux/semaphore.h>
#include <linux/cdev.h>
#include <linux/kdev_t.h>
#include <linux/device.h>
#include <linux/flipper.h>

FLIPPER_ARRAY_TYPE flipper_bitfield[FLIPPER_ARRAY_SIZE] = {0};
EXPORT_SYMBOL(flipper_bitfield);

#define CHARSIZE (sizeof(char) * 8)
static char flipper_bitfield_cached[FLIPPER_ENTRIES / CHARSIZE
                                    + (FLIPPER_ENTRIES % CHARSIZE == 0 ? 0 : 1)];

static dev_t first;
static struct cdev c_dev;
static struct class *cl;
static struct semaphore sem;

static inline int flipper_open(struct inode *inode, struct file *filp) {
    if (down_interruptible(&sem)) {
        printk(KERN_INFO " could not hold semaphore");
        return -1;
    } else {
        unsigned long long i;
        for (i = 0; i < FLIPPER_ENTRIES; i++) {
            if (i % CHARSIZE == 0)
                flipper_bitfield_cached[i / CHARSIZE] = (char)0x00;
            if (TEST_FLIPPER_BIT(i))
                flipper_bitfield_cached[i / CHARSIZE] |= 1 << (i % CHARSIZE);
        }
        return 0;
    }
}

static inline int flipper_release(struct inode *inode, struct file *filp) {
    up(&sem);
    return 0;
}

static inline ssize_t flipper_read(struct file *file, char __user *buf, size_t lbuf,
                                   loff_t *ppos) {
    int nbytes, maxbytes, bytes_to_do;
    maxbytes = sizeof(flipper_bitfield_cached) - *ppos;
    bytes_to_do = maxbytes > lbuf ? lbuf : maxbytes;
    nbytes = bytes_to_do - copy_to_user(buf, (flipper_bitfield_cached + *ppos), bytes_to_do);
    *ppos += nbytes;
    return nbytes;
}

static inline loff_t flipper_lseek(struct file *file, loff_t offset, int orig) {
    loff_t testpos;
    switch (orig) {
    case SEEK_SET:
        testpos = offset;
        break;
    case SEEK_CUR:
        testpos = file->f_pos + offset;
        break;
    case SEEK_END:
        testpos = sizeof(flipper_bitfield_cached) + offset;
        break;
    default:
        return -EINVAL;
    }
    testpos = testpos < sizeof(flipper_bitfield_cached) ? testpos
                                                        : sizeof(flipper_bitfield_cached);
    testpos = testpos >= 0 ? testpos : 0;
    file->f_pos = testpos;

    return testpos;
}

static struct file_operations fops = {.read = flipper_read,
                                      .llseek = flipper_lseek,
                                      .open = flipper_open,
                                      .release = flipper_release};

static inline int __init flipper_init(void) {
    int init_result = alloc_chrdev_region(&first, 0, 1, "flipper");

    if (init_result < 0) {
        printk(KERN_ALERT "Device Registration failed\n");
        return -1;
    }

    if ((cl = class_create(THIS_MODULE, "chardev")) == NULL) {
        printk(KERN_ALERT "Class creation failed\n");
        unregister_chrdev_region(first, 1);
        return -1;
    }

    if (device_create(cl, NULL, first, NULL, "flipper") == NULL) {
        printk(KERN_ALERT "Device creation failed\n");
        class_destroy(cl);
        unregister_chrdev_region(first, 1);
        return -1;
    }

    cdev_init(&c_dev, &fops);

    if (cdev_add(&c_dev, first, 1) == -1) {
        printk(KERN_ALERT "Device addition failed\n");
        device_destroy(cl, first);
        class_destroy(cl);
        unregister_chrdev_region(first, 1);
        return -1;
    }

    sema_init(&sem, 1);

    return 0;
}

static inline void __exit flipper_exit(void) {
    cdev_del(&c_dev);
    device_destroy(cl, first);
    class_destroy(cl);
    unregister_chrdev_region(first, 1);
}

module_init(flipper_init);
module_exit(flipper_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Bernhard Heinloth <bernhard@heinloth.net>");
