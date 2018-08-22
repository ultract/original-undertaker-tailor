/*
 *   undertaker - analyze preprocessor blocks in code
 *
 * Copyright (C) 2009-2012 Reinhard Tartler <tartler@informatik.uni-erlangen.de>
 * Copyright (C) 2009-2011 Julio Sincero <Julio.Sincero@informatik.uni-erlangen.de>
 * Copyright (C) 2010-2011 Christian Dietrich <christian.dietrich@informatik.uni-erlangen.de>
 * Copyright (C) 2013-2014 Stefan Hengelein <stefan.hengelein@fau.de>
 * Copyright (C) 2015 Andreas Ruprecht <andreas.ruprecht@fau.de>
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

#include "BlockDefectAnalyzer.h"
#include "ConditionalBlock.h"
#include "StringJoiner.h"
#include "SatChecker.h"
#include "ModelContainer.h"
#include "ConfigurationModel.h"
#include "Logging.h"
#include "Tools.h"
#include "exceptions/CNFBuilderError.h"

#include <fstream>


/************************************************************************/
/* BlockDefectAnalyzer                                                  */
/************************************************************************/

std::string BlockDefectAnalyzer::getBlockPrecondition(ConditionalBlock *cb,
                                                      const ConfigurationModel *model) {
    StringJoiner formula;

    /* Adding block and code constraints extraced from code sat stream */
    std::string code_formula = cb->getCodeConstraints();
    formula.push_back(cb->getName());
    formula.push_back(code_formula);

    if (model) {
        /* Adding kconfig constraints and kconfig missing */
        std::set<std::string> missingSet;
        std::string kconfig_formula;
        // add file precondition
        code_formula += " && ";
        code_formula += cb->getBuildSystemCondition();
        formula.push_back(cb->getBuildSystemCondition());
        model->doIntersect(code_formula, cb->getFile()->getDefineChecker(), missingSet,
                           kconfig_formula);
        formula.push_back(kconfig_formula);
        if (model->isComplete())
            formula.push_back(ConfigurationModel::getMissingItemsConstraints(missingSet));
    }
    return formula.join("\n&& ");
}

static const BlockDefect *analyzeBlock_helper(ConditionalBlock *block,
                                              ConfigurationModel *main_model) {
    BlockDefect *defect = new DeadBlockDefect(block);

    // If this is neither an Implementation, Configuration nor Referential *dead*,
    // then destroy the analysis and retry with an Undead Analysis
    if (!defect->isDefect(main_model, true)) {
        delete defect;
        defect = new UndeadBlockDefect(block);

        // No defect found, block seems OK
        if (!defect->isDefect(main_model, true)) {
            delete defect;
            return nullptr;
        }
    }
    assert(defect->defectType() != BlockDefect::DEFECTTYPE::None);

    // Check NoKconfig defect after (un)dead analysis
    if (defect->isNoKconfigDefect(main_model))
        defect->setDefectType(BlockDefect::DEFECTTYPE::NoKconfig);

    // Save defectType in block
    block->defectType = defect->defectType();

    // defects in arch specific files do not require a crosscheck and are global defects, since
    // they are not compileable for other architectures
    if (block->getFile()->getSpecificArch() != "") {
        defect->markAsGlobal();
        return defect;
    }

    // Implementation (i.e., Code) or NoKconfig defects do not require a crosscheck
    if (!main_model || !defect->needsCrosscheck())
        return defect;

    for (const auto &entry : ModelContainer::getInstance()) { // pair<string, ConfigurationModel *>
        const ConfigurationModel *model = entry.second;
        // don't check the main model twice
        if (model == main_model)
            continue;

        if (!defect->isDefect(model))
            return defect;
    }
    defect->markAsGlobal();
    return defect;
}

const BlockDefect *BlockDefectAnalyzer::analyzeBlock(ConditionalBlock *block,
                                                     ConfigurationModel *main_model) {
    try {
        return analyzeBlock_helper(block, main_model);
    } catch (CNFBuilderError &e) {
        Logging::error("Couldn't process ", block->getFile()->getFilename(), ":", block->getName(),
                       ": ", e.what());
    } catch (std::bad_alloc &) {
        Logging::error("Couldn't process ", block->getFile()->getFilename(), ":", block->getName(),
                       ": Out of Memory.");
    }
    return nullptr;
}

/************************************************************************/
/* BlockDefect                                                          */
/************************************************************************/

const std::string BlockDefect::defectTypeToString() const {
    switch (_defectType) {
    case DEFECTTYPE::None:
        return "";  // Nothing to write
    case DEFECTTYPE::Implementation:
        return "code";
    case DEFECTTYPE::Configuration:
        return "kconfig";
    case DEFECTTYPE::Referential:
        return "missing";
    case DEFECTTYPE::NoKconfig:
        return "no_kconfig";
    case DEFECTTYPE::BuildSystem:
        return "kbuild";
    default:
        assert(false);
    }
    return "";
}

bool BlockDefect::needsCrosscheck() const {
    switch (_defectType) {
    case DEFECTTYPE::None:
    case DEFECTTYPE::Implementation:
    case DEFECTTYPE::NoKconfig:
        return false;
    default:
        // skip crosschecking if we already know that it is global
        return !_isGlobal;
    }
}

std::string BlockDefect::getDefectReportFilename() const {
    StringJoiner fname_joiner;
    fname_joiner.push_back(_cb->getFile()->getFilename());
    fname_joiner.push_back(_cb->getName());
    fname_joiner.push_back(defectTypeToString());

    if (_isGlobal || _defectType == DEFECTTYPE::NoKconfig)
        fname_joiner.push_back("globally");
    else
        fname_joiner.push_back("locally");

    fname_joiner.push_back(_suffix);
    return fname_joiner.join(".");
}

bool BlockDefect::isNoKconfigDefect(const ConfigurationModel *model) const {
    if (!model)
        return true;

    std::string expr;
    if (_cb->isElseBlock()) {
        // Check prior blocks
        const ConditionalBlock *prev = _cb->getPrev();
        while (prev) {
            if (prev->defectType != DEFECTTYPE::NoKconfig)
                return false;
            prev = prev->getPrev();
        }
    } else if (_cb == _cb->getFile()->topBlock()) {
        // If current block is the file, take the entire formula.
        expr = _formula;
    } else {
        // Otherwise, take the expression.
        expr = _cb->ifdefExpression();
    }
    for (const std::string &str : undertaker::itemsOfString(expr))
        if (model->inConfigurationSpace(str))
            return false;

    return true;
}

void BlockDefect::writeReportToFile(bool skip_no_kconfig) const {
    if ((skip_no_kconfig && _defectType == DEFECTTYPE::NoKconfig)
        || _defectType == DEFECTTYPE::None)
        return;
    const std::string filename = getDefectReportFilename();

    std::ofstream out(filename);

    if (!out.good()) {
        Logging::error("failed to open ", filename, " for writing ");
        return;
    }
    Logging::info("creating ", filename);
    out << "#" << _cb->getName() << ":" << _cb->filename() << ":" << _cb->lineStart() << ":"
        << _cb->colStart() << ":" << _cb->filename() << ":" << _cb->lineEnd() << ":"
        << _cb->colEnd() << ":" << std::endl;
    out << _formula << std::endl;
    // for all processed arches, add the specific defect type to the defect report
    if (defectMap.size() > 0)
        out << [this]() {
            std::string retstr("\nArch -> Defect Type:\n");
            for (const auto &entry : defectMap) {
                retstr += entry.first;
                retstr += " -> ";
                retstr += entry.second;
                retstr += "\n";
            }
            return retstr;
        }();
    out.close();
}

/************************************************************************/
/* DeadBlockDefect                                                      */
/************************************************************************/

DeadBlockDefect::DeadBlockDefect(ConditionalBlock *cb) : BlockDefect(cb) {
    this->_suffix = "dead";
}

void DeadBlockDefect::reportMUS(ConfigurationModel *main_model) const {
    // MUS only works on {code, kconfig} dead blocks
    if (_defectType == DEFECTTYPE::None)
        return;
    // call Satchecker and get the CNF-Object
    SatChecker sc(main_model);
    sc(_musFormula);
    if(!sc.checkMUS())
        return;

    // create filename for mus-defect report and open the outputfilestream
    std::string filename = this->getDefectReportFilename() + ".mus";
    std::ofstream ofs(filename);
    if (!ofs.good()) {
        Logging::error("Failed to open ", filename, " for writing.");
        return;
    }
    Logging::info("creating ", filename);
    // print formula and prepend some statistics about the picomus performance
    sc.writeMUS(ofs);
}

bool DeadBlockDefect::isDefect(const ConfigurationModel *model, bool is_main_model) {
    StringJoiner formula;

    std::string code_formula = _cb->getCodeConstraints();
    formula.push_back(_cb->getName());
    formula.push_back(code_formula);
    _formula = formula.join("\n&&\n");

    // check for code defect
    SatChecker sc;
    if (!sc(_formula)) {
        _defectType = DEFECTTYPE::Implementation;
        _isGlobal = true;
        _musFormula = _formula;
        return true;
    }
    // we don't have a model, no further analyses possible
    if (!model)
        return false;

    // check for kconfig defect
    std::set<std::string> missingSet;
    std::string kconfig_formula;
    std::set<std::string> kconfigItems = model->doIntersect(code_formula,
                                                            _cb->getFile()->getDefineChecker(),
                                                            missingSet, kconfig_formula);
    formula.push_back(kconfig_formula);

    // increment sc with kconfig_formula and load model if necessary
    if (model->getModelVersionIdentifier() == "cnf")
        sc.loadCnfModel(model);
    if (!sc(kconfig_formula)) {
        _formula = formula.join("\n&&\n");
        // save formula for mus analysis when we are analysing the main_model
        if (is_main_model)
            _musFormula = _formula;
        if (_defectType != DEFECTTYPE::BuildSystem)
            _defectType = DEFECTTYPE::Configuration;
        defectMap.emplace(ModelContainer::lookupArch(model), "kconfig");
        return true;
    }

    // check for kbuild defect
    std::string precondition = _cb->getBuildSystemCondition();
    std::string precondition_formula;
    model->doIntersect(precondition, nullptr, missingSet, precondition_formula, &kconfigItems);
    if (precondition_formula.size() > 0)
        precondition_formula += "\n&& ";
    precondition_formula += precondition;
    formula.push_back(precondition_formula);
    if (!sc(precondition_formula)) {
        _formula = formula.join("\n&&\n");
        if (is_main_model)
            _musFormula = _formula;
        _defectType = DEFECTTYPE::BuildSystem;
        defectMap.emplace(ModelContainer::lookupArch(model), "kbuild");
        return true;
    }

    // An incomplete model (not all symbols mentioned) can't generate referential errors
    if (!model->isComplete())
        return false;

    // check for missing defect
    std::string missing = ConfigurationModel::getMissingItemsConstraints(missingSet);
    if (!sc(missing)) {
        formula.push_back(missing);
        _formula = formula.join("\n&&\n");
        if (_defectType != DEFECTTYPE::Configuration && _defectType != DEFECTTYPE::BuildSystem)
            _defectType = DEFECTTYPE::Referential;
        defectMap.emplace(ModelContainer::lookupArch(model), "missing");
        // save formula for mus analysis when we are analysing the main_model
        if (is_main_model)
            _musFormula = _formula;
        return true;
    }
    return false;
}

/************************************************************************/
/* UndeadBlockDefect                                                    */
/************************************************************************/

UndeadBlockDefect::UndeadBlockDefect(ConditionalBlock *cb) : BlockDefect(cb) {
    this->_suffix = "undead";
}

bool UndeadBlockDefect::isDefect(const ConfigurationModel *model, bool) {
    StringJoiner formula;
    const ConditionalBlock *parent = _cb->getParent();

    // no parent -> it's B00 -> impossible to be undead
    if (!parent)
        return false;

    std::string code_formula = _cb->getCodeConstraints();
    formula.push_back("( " + parent->getName() + " && ! " + _cb->getName() + " )");
    formula.push_back(code_formula);
    _formula = formula.join("\n&&\n");

    // check for code defect
    SatChecker sc;
    if (!sc(_formula)) {
        _defectType = DEFECTTYPE::Implementation;
        _isGlobal = true;
        return true;
    }
    // we don't have a model, no further analyses possible
    if (!model)
        return false;

    // check for kconfig defect
    std::set<std::string> missingSet;
    std::string kconfig_formula;
    std::set<std::string> kconfigItems = model->doIntersect(code_formula,
                                                            _cb->getFile()->getDefineChecker(),
                                                            missingSet, kconfig_formula);
    formula.push_back(kconfig_formula);

    // increment sc with kconfig_formula and load model if necessary
    if (model->getModelVersionIdentifier() == "cnf")
        sc.loadCnfModel(model);
    if (!sc(kconfig_formula)) {
        _formula = formula.join("\n&&\n");
        if (_defectType != DEFECTTYPE::BuildSystem)
            _defectType = DEFECTTYPE::Configuration;
        defectMap.emplace(ModelContainer::lookupArch(model), "kconfig");
        return true;
    }

    // check for kbuild defect
    std::string precondition = _cb->getBuildSystemCondition();
    std::string precondition_formula;
    model->doIntersect(precondition, nullptr, missingSet, precondition_formula, &kconfigItems);
    if (precondition_formula.size() > 0)
        precondition_formula += "\n&& ";
    precondition_formula += precondition;
    formula.push_back(precondition_formula);
    if (!sc(precondition_formula)) {
        _formula = formula.join("\n&&\n");
        _defectType = DEFECTTYPE::BuildSystem;
        defectMap.emplace(ModelContainer::lookupArch(model), "kbuild");
        return true;
    }

    // An incomplete model (not all symbols mentioned) can't generate referential errors
    if (!model->isComplete())
        return false;

    // check for missing defect
    std::string missing = ConfigurationModel::getMissingItemsConstraints(missingSet);
    if (!sc(missing)) {
        formula.push_back(missing);
        _formula = formula.join("\n&&\n");
        if (_defectType != DEFECTTYPE::Configuration && _defectType != DEFECTTYPE::BuildSystem)
            _defectType = DEFECTTYPE::Referential;
        defectMap.emplace(ModelContainer::lookupArch(model), "missing");
        return true;
    }
    return false;
}
