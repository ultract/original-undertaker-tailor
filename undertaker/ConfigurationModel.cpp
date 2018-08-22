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

#include "ConfigurationModel.h"
#include "StringJoiner.h"
#include "Tools.h"
#include "Logging.h"


std::string ConfigurationModel::getMissingItemsConstraints(const std::set<std::string> &missing) {
    StringJoiner sj;
    for (const std::string &str : missing)
        sj.push_back(str);

    if (sj.size() > 0)
        return "( ! ( " + sj.join(" || ") + " ) )";
    return {};
}

std::set<std::string> ConfigurationModel::doIntersect(const std::string exp,
                                                      const std::function<bool(std::string)> &c,
                                                      std::set<std::string> &missing,
                                                      std::string &intersected,
                                                      std::set<std::string> *exclude_set) const {
    std::set<std::string> start_items = undertaker::itemsOfString(exp);

    StringJoiner sj;
    doIntersectPreprocess(start_items, sj, exclude_set);  // preprocess depending on model type

    // add all items from start_items into 'sj' if they are in the model && in ALWAYS_{ON,OFF}
    // and if they are not in the model, check if they could be missing
    const StringList *always_on = getWhitelist();
    const StringList *always_off = getBlacklist();
    for (const std::string &str : start_items) {
        if (containsSymbol(str)) {
            if (always_on) {
                const auto &cit = std::find(always_on->begin(), always_on->end(), str);
                if (cit != always_on->end())  // str is found
                    sj.push_back(str);
            }
            if (always_off) {
                const auto &cit = std::find(always_off->begin(), always_off->end(), str);
                if (cit != always_off->end())  // str is found
                    sj.push_back("!" + str);
            }
        } else {
            // check if the symbol might be in the model space. if not it can't be missing!
            if (!inConfigurationSpace(str))
                continue;
            // if we are given a checker for items, skip if it doesn't pass the test
            if (c && !c(str))
                continue;
            /* free variables or constant values are never missing */
            if (!undertaker::starts_with(str, "__FREE__")
                    && !undertaker::starts_with(str, "CONFIG_CVALUE_"))
                missing.insert(str);
        }
    }
    intersected = sj.join("\n&& ");
    Logging::debug("Out of ", start_items.size(), " items ", missing.size(),
                   " have been put in the MissingSet");
    return start_items;
}

void ConfigurationModel::addFeatureToWhitelist(const std::string &feature) {
    addMetaValue("ALWAYS_ON", feature);
}

const StringList *ConfigurationModel::getWhitelist() const {
    return getMetaValue("ALWAYS_ON");
}

void ConfigurationModel::addFeatureToBlacklist(const std::string &feature) {
    addMetaValue("ALWAYS_OFF", feature);
}

const StringList *ConfigurationModel::getBlacklist() const {
    return getMetaValue("ALWAYS_OFF");
}

bool ConfigurationModel::isComplete() const {
    // metaValue is only present (!= nullptr) when conf_space is incomplete
    return getMetaValue("CONFIGURATION_SPACE_INCOMPLETE") == nullptr;
}

bool ConfigurationModel::inConfigurationSpace(const std::string &symbol) const {
    return boost::regex_match(symbol, _inConfigurationSpace_regexp);
}
