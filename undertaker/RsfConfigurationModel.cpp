/*
 *   undertaker - analyze preprocessor blocks in code
 *
 * Copyright (C) 2009-2012 Reinhard Tartler <tartler@informatik.uni-erlangen.de>
 * Copyright (C) 2012 Ralf Hackner <rh@ralf-hackner.de>
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

#ifdef DEBUG
#define BOOST_FILESYSTEM_NO_DEPRECATED
#endif

#include "RsfConfigurationModel.h"
#include "Tools.h"
#include "StringJoiner.h"
#include "RsfReader.h"
#include "Logging.h"

#include <boost/filesystem.hpp>
#include <boost/regex.hpp>
#include <stack>


RsfConfigurationModel::RsfConfigurationModel(const std::string &filename) {
    boost::filesystem::path filepath(filename);
    _name = filepath.stem().string();
    // load .model file (modelcontainer checks if filename is valid)
    _model = new RsfReader(filename);
    // load .rsf file (or create empty ItemRsfReader if file is not existent)
    if (filepath.extension() == ".model") {
        filepath.replace_extension(".rsf");
        if (boost::filesystem::exists(filepath))
            _rsf = new ItemRsfReader(filepath.string());
    }
    if (nullptr == _rsf) {
        Logging::warn("Couldn't open ", filepath.string(), " checking symbol types will fail");
        _rsf = new ItemRsfReader();  // create empty ItemRsfReader
    }
    // set configuration space regex
    const StringList *cfg_space_regex = _model->getMetaValue("CONFIGURATION_SPACE_REGEX");
    if (cfg_space_regex != nullptr && cfg_space_regex->size() > 0) {
        Logging::info("Set configuration space regex to '", cfg_space_regex->front(), "'");
        _inConfigurationSpace_regexp = boost::regex(cfg_space_regex->front());
    } else {
        _inConfigurationSpace_regexp = boost::regex("^CONFIG_[^ ]+$");
    }
    if (_model->size() == 0)
        // if the model is empty (e.g., if /dev/null was loaded), it cannot possibly be complete
        _model->addMetaValue("CONFIGURATION_SPACE_INCOMPLETE", "1");
}

RsfConfigurationModel::~RsfConfigurationModel() {
    delete _model;
    delete _rsf;
}

void RsfConfigurationModel::extendWithInterestingItems(std::set<std::string> &workingSet) const {
    std::stack<std::string> workingStack;
    /* Initialize the working stack with the given elements */
    for (const std::string &str : workingSet)
        workingStack.push(str);
    while (!workingStack.empty()) {
        const std::string *item = _model->getValue(workingStack.top());
        workingStack.pop();
        if (item != nullptr && *item != "") {
            for (const std::string &str : undertaker::itemsOfString(*item)) {
                /* Item already seen? continue */
                if (workingSet.count(str) == 0) {
                    workingStack.push(str);
                    workingSet.insert(str);
                }
            }
        }
    }
}

void RsfConfigurationModel::doIntersectPreprocess(std::set<std::string> &item_set,
                                                  StringJoiner &sj,
                                                  std::set<std::string> *exclude_set) const {
    const StringList *always_on = getWhitelist();
    const StringList *always_off = getBlacklist();

    // ALWAYS_ON items and their transitive dependencies always need to appear in the slice.
    if (always_on)
        for (const std::string &str : *always_on)
            item_set.insert(str);

    extendWithInterestingItems(item_set);

    if (exclude_set)
        for (const std::string &str : *exclude_set)
            item_set.erase(str);

    // For all symbols in 'item_set', retrieve the formula from the model and push it into sj.
    for (const std::string &str : item_set) {
        const std::string *item = _model->getValue(str);
        if (item != nullptr && *item != "")
            sj.push_back("(" + str + " -> (" + *item + "))");
    }
    // There is no point in adding the formulae of always_off items into sj, since we push the
    // negated always_off symbol into sj, false -> {true,false}
    if (always_off) {
        for (const std::string &str : *always_off)
            item_set.insert(str);
        // If there were ALWAYS_OFF items, add their transitive dependencies as well
        extendWithInterestingItems(item_set);
    }
}

bool RsfConfigurationModel::isBoolean(const std::string &item) const {
    const std::string *value = _rsf->getValue(item);
    if (value && *value == "boolean")
        return true;
    return false;
}

bool RsfConfigurationModel::isTristate(const std::string &item) const {
    const std::string *value = _rsf->getValue(item);
    if (value && *value == "tristate")
        return true;
    return false;
}

std::string RsfConfigurationModel::getType(const std::string &feature_name) const {
    static const boost::regex item_regexp("^CONFIG_([0-9A-Za-z_]+?)(_MODULE)?$");
    boost::smatch what;

    if (boost::regex_match(feature_name, what, item_regexp)) {
        std::string item = what[1];
        const std::string *value = _rsf->getValue(item);

        if (value) {
            std::string type = *value;
            std::transform(type.begin(), type.end(), type.begin(), ::toupper);
            return type;
        } else {
            return "MISSING";
        }
    }
    return "#ERROR";
}

bool RsfConfigurationModel::containsSymbol(const std::string &symbol) const {
    return _model->find(symbol) != _model->end();
}

void RsfConfigurationModel::addMetaValue(const std::string &key, const std::string &val) const {
    return _model->addMetaValue(key, val);
}

const StringList *RsfConfigurationModel::getMetaValue(const std::string &key) const {
    return _model->getMetaValue(key);
}
