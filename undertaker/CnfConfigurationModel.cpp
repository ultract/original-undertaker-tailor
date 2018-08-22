/*
 *   undertaker - analyze preprocessor blocks in code
 *
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

#include "CnfConfigurationModel.h"
#include "Logging.h"
#include "PicosatCNF.h"
#include "StringJoiner.h"
#include "Tools.h"

#include <boost/filesystem.hpp>
#include <boost/regex.hpp>


CnfConfigurationModel::CnfConfigurationModel(const std::string &filename) {
    boost::filesystem::path filepath(filename);
    _name = filepath.stem().string();

    _cnf = new kconfig::PicosatCNF();
    _cnf->readFromFile(filename);

    const StringList *configuration_space_regex = _cnf->getMetaValue("CONFIGURATION_SPACE_REGEX");
    if (configuration_space_regex != nullptr && configuration_space_regex->size() > 0) {
        Logging::info("Set configuration space regex to '", configuration_space_regex->front(),
                      "'");
        _inConfigurationSpace_regexp = boost::regex(configuration_space_regex->front());
    } else {
        _inConfigurationSpace_regexp = boost::regex("^CONFIG_[^ ]+$");
    }
    if (_cnf->getVarCount() == 0) {
        // if the model is empty (e.g., if /dev/null was loaded), it cannot possibly be complete
        _cnf->addMetaValue("CONFIGURATION_SPACE_INCOMPLETE", "1");
    }
}

CnfConfigurationModel::~CnfConfigurationModel() { delete _cnf; }

bool CnfConfigurationModel::isBoolean(const std::string &item) const {
    return _cnf->getSymbolType(item) == K_S_BOOLEAN;
}

bool CnfConfigurationModel::isTristate(const std::string &item) const {
    return _cnf->getSymbolType(item) == K_S_TRISTATE;
}

std::string CnfConfigurationModel::getType(const std::string &feature_name) const {
    static const boost::regex item_regexp("^CONFIG_([0-9A-Za-z_]+?)(_MODULE)?$");
    boost::smatch what;

    if (boost::regex_match(feature_name, what, item_regexp)) {
        std::string item = what[1];
        int type = _cnf->getSymbolType(item);
        static const std::string types[]{"MISSING", "BOOLEAN", "TRISTATE", "INTEGER",
                                         "HEX",     "STRING",  "other"};
        return types[type];
    }
    return "#ERROR";
}

bool CnfConfigurationModel::containsSymbol(const std::string &symbol) const {
    return undertaker::starts_with(symbol, "FILE_") || _cnf->getAssociatedSymbol(symbol) != nullptr;
}

void CnfConfigurationModel::addMetaValue(const std::string &key, const std::string &val) const {
    return _cnf->addMetaValue(key, val);
}

const StringList *CnfConfigurationModel::getMetaValue(const std::string &key) const {
    return _cnf->getMetaValue(key);
}
