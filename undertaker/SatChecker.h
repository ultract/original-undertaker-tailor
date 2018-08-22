/*
 *   undertaker - analyze preprocessor blocks in code
 *
 * Copyright (C) 2009-2013 Reinhard Tartler <tartler@informatik.uni-erlangen.de>
 * Copyright (C) 2009-2011 Julio Sincero <Julio.Sincero@informatik.uni-erlangen.de>
 * Copyright (C) 2010-2011 Christian Dietrich <christian.dietrich@informatik.uni-erlangen.de>
 * Copyright (C) 2012 Christoph Egger <siccegge@informatik.uni-erlangen.de>
 * Copyright (C) 2012 Ralf Hackner <sirahack@informatik.uni-erlangen.de>
 * Copyright (C) 2013-2014 Stefan Hengelein <stefan.hengelein@fau.de>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// -*- mode: c++ -*-
#ifndef sat_checker_h__
#define sat_checker_h__

#include "PicosatCNF.h"

#include <map>
#include <set>
#include <list>
#include <memory>

typedef std::set<std::string> MissingSet;

class ConfigurationModel;
class CppFile;


/************************************************************************/
/* SatChecker                                                           */
/************************************************************************/

class SatChecker {
    enum class state {no, yes, module};

    struct musData {
        std::string minimized_formula;
        int vars = 0, lines = 0;
    } musData;

public:
    explicit SatChecker(const ConfigurationModel * = nullptr,
                        Picosat::SATMode mode = Picosat::SAT_MAX);

    virtual ~SatChecker() {};

    /**
     * Checks the given string with an sat solver
     * @param formula the formula to be checked
     * @returns true, if satisfiable, false otherwise
     * @throws CnfBuilderError when a syntax error occured
     */
    bool operator()(const std::string &formula);

    static bool check(const std::string &sat);

    /**
     * \brief Representation of a variable selection
     *
     * The solutions in this map contain all kinds of SAT variables,
     * including block variables (e.g., B42), comparator (fake)
     * variables (e.g., COMP_42) and item variables (e.g.,
     * CONFIG_ACPI_MODULES).
     *
     *   - key:   something like 'B42'
     *   - value: true if set, false if unset or unknown
     */
    struct AssignmentMap : public std::map<std::string, bool> {
        /**
            * \brief order independent content comparison
            *
            * This method compares if two assignments are equivalent.
            */
        bool operator==(const AssignmentMap &other) const {
            for (const auto &entry : *this) {  // pair<string, bool>
                auto ot = other.find(entry.first);
                if (ot == other.end() || (*ot).second != entry.second)
                    return false;
            }
            return true;
        }

        /**
         * \brief collect enabled blocks
         *
         * The idea of this method is to set all blocks that are enabled
         * in a bitvector. Hereby, the position of each bit in the
         * vector represents the block number. 1 represents a selected
         * block. Bits are only set and never unset.
         */
        void setEnabledBlocks(std::vector<bool> &blocks);

        /**
         * \brief format solutions (kconfig specific)
         *
         * This method filters out comparators and block variables from the
         * given AssignmentMap solution.  Additionally,
         * CONFIG_ACPI_MODULE and the like lead to the CONFIG_ACPI variable
         * being set to '=m'. This output resembles a partial KConfig
         * selection.
         *
         * \param out an output stream on which the solution shall be printed
         * \param missingSet set of items that are not available in the model
         */
        int formatKconfig(std::ostream &out, const MissingSet &missingSet) const;

        /**
         * \brief format solutions (model)
         *
         *  Print out all assignments that are in the configuration space
         *
         * \param out an output stream on which the solution shall be
         *     printed
         * \param configuration model, that specifies the
         *     configuration space
         */
        int formatModel(std::ostream &out, const ConfigurationModel *model) const;

        /**
         * \brief format solutions (all)
         *
         *  Print out all assignments!
         *
         * \param out an output stream on which the solution shall be
         *     printed
         */
        int formatAll(std::ostream &out) const;

        /**
         * \brief format solutions as CPP compatible arguments
         *
         *  Print out all cpp symbols
         *
         * \param out an output stream on which the solution shall be
         *     printed
         */
        int formatCPP(std::ostream &out, const ConfigurationModel *model) const;

        /**
         * \brief pipe all activated blocks into command
         *
         * \param CPP file which is basis for the analysis
         * \param cmd the command that is spawned
         */
        int formatExec(const CppFile &file, const char *cmd) const;

        /**
         * \brief comments out all unselected blocks
         *
         * \param out the output stream to work on
         * \param file the corresponding CppFile for this AssignmentMap
         */
        int formatCommented(std::ostream &out, const CppFile &file) const;

        /**
         * \brief combination of formatCPP, formatCommented and formatKconfig.
         *
         * This output format uses all of formatCPP,
         * formatCommented and formatKconfig. Unlike the other methods, this mode
         * produces three additional files with the content.
         *
         * \param file passed to formatCommented
         * \param model passed to formatCPP
         * \param missingSet passwd to formatKconfig
         * \param number a running numer that is encoded in the filename
         */
        int formatCombined(const CppFile &file, const ConfigurationModel *model,
            const MissingSet& missingSet, unsigned number) const;
    }; // end struct AssignmentMap

    // After doing the check, you can get the assignments for the formula
    const AssignmentMap &getAssignment();

    // Prints the assignments in an human readable way on stdout
    static void pprintAssignments(std::ostream &out, const std::list<AssignmentMap> solution,
                                  const ConfigurationModel *model, const MissingSet &missingSet);

    void loadCnfModel(const ConfigurationModel *);

    bool checkMUS();
    void writeMUS(std::ostream &out, bool writeStatistics = true) const;

protected:
    std::unique_ptr<kconfig::PicosatCNF> _cnf;
    AssignmentMap assignmentTable;
};

/************************************************************************/
/* BaseExpressionSatChecker                                             */
/************************************************************************/

class BaseExpressionSatChecker : public SatChecker {
public:
    explicit BaseExpressionSatChecker(std::string base_expression,
                                      const ConfigurationModel * = nullptr);
    virtual ~BaseExpressionSatChecker() {}
    bool operator()(const std::set<std::string> &assumeSymbols);
};
#endif
