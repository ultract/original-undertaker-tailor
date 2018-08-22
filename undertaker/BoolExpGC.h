// -*- mode: c++ -*-
/*
 *   boolean framework for undertaker and satyr
 *
 * Copyright (C) 2012 Ralf Hackner <rh@ralf-hackner.de>
 * Copyright (C) 2013-2014 Stefan Hengelein <stefan.hengelein@fau.de>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

#ifndef KCONFIG_BOOLEXPGC_H
#define KCONFIG_BOOLEXPGC_H

#include "bool.h"
#include "BoolVisitor.h"

namespace kconfig {
    class BoolExpGC : public BoolVisitor {
    public:
        void sweep(BoolExp *root = nullptr);

        void trash(BoolExp *e) { e->accept(this); }

    protected:
        void visit(BoolExp *)      final override {}
        void visit(BoolExpAnd *)   final override {}
        void visit(BoolExpOr *)    final override {}
        void visit(BoolExpNot *)   final override {}
        void visit(BoolExpConst *) final override {}
        void visit(BoolExpVar *)   final override {}
        void visit(BoolExpImpl *)  final override {}
        void visit(BoolExpEq *)    final override {}
        void visit(BoolExpCall *)  final override {}
        void visit(BoolExpAny *)   final override {}
    };
} // namespace kconfig
#endif
