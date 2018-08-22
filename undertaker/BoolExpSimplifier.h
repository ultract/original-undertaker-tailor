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

#ifndef KCONFIG_BOOLSIMPLIFIER_H
#define KCONFIG_BOOLSIMPLIFIER_H

#include "bool.h"
#include "BoolVisitor.h"

namespace kconfig {
    class BoolExpSimplifier : public BoolVisitor {
    public:
        BoolExp *getResult(void) const {
            return static_cast<BoolExp *>(this->result);
        }

    protected:
        void visit(BoolExp *e)      final override;
        void visit(BoolExpAnd *e)   final override;
        void visit(BoolExpOr *e)    final override;
        void visit(BoolExpNot *e)   final override;
        void visit(BoolExpConst *e) final override;
        void visit(BoolExpVar *e)   final override;
        void visit(BoolExpImpl *e)  final override;
        void visit(BoolExpEq *e)    final override;
        void visit(BoolExpCall *e)  final override;
        void visit(BoolExpAny *e)   final override;
    };
} // namespace kconfig
#endif
