/*
 *   undertaker - analyze preprocessor blocks in code
 *
 * Copyright (C) 2009-2012 Reinhard Tartler <tartler@informatik.uni-erlangen.de>
 * Copyright (C) 2009-2011 Julio Sincero <Julio.Sincero@informatik.uni-erlangen.de>
 * Copyright (C) 2010-2011 Christian Dietrich <christian.dietrich@informatik.uni-erlangen.de>
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

#include "RsfReader.h"
#include "Logging.h"

#include <sstream>
#include <fstream>
#include <algorithm>


/************************************************************************/
/* RsfReader - to read .model files                                     */
/************************************************************************/

// remove leading / trailing '"' char from string s
static inline void trim(std::string &s) {
    if (s.front() == '"')
        s.erase(0, 1);
    if (s.back() == '"')
        s.pop_back();
}

RsfReader::RsfReader(const std::string &filename, std::string metaflag) {
    std::ifstream f(filename);
    if (!f.good()) {
        Logging::error("couldn't open modelfile: ", filename);
        return;
    }
    std::string line;
    while (std::getline(f, line)) {
        if (line == "")  // skip empty lines
            continue;
        std::stringstream ss(line);
        std::string key;
        ss >> key;
        if (metaflag != "" && key == metaflag) {
            // if the current line contains meta information, add them to the meta_information map
            ss >> key;
            std::deque<std::string> meta_items;
            std::string item;
            while (ss >> item) {
                if (item.back() != '"') {  // special case for meta items containing white spaces
                    std::string tmp;
                    std::getline(ss, tmp, '"');
                    item += tmp;
                }
                trim(item);
                meta_items.emplace_back(item);
            }
            meta_information.emplace(key, meta_items);
        } else {
            std::string formula;
            ss >> std::ws;  // skip leading whitespaces
            std::getline(ss, formula);
            trim(formula);
            emplace(key, formula);
        }
    }
}

void RsfReader::print_contents(std::ostream &out) {
    for (const auto &entry : *this)  // pair<string, string>
        out << entry.first << " : " << entry.second << std::endl;
}

const std::string *RsfReader::getValue(const std::string &key) const {
    auto i = find(key);
    if (i == end())  // key not found
        return nullptr;
    return &(i->second);
}

const StringList *RsfReader::getMetaValue(const std::string &key) const {
    const auto &it = meta_information.find(key); // pair<string, StringList>
    if (it == meta_information.end())  // key not found
        return nullptr;
    return &(it->second);
}

void RsfReader::addMetaValue(const std::string &key, const std::string &value) {
    StringList &values = meta_information[key];
    if (std::find(values.begin(), values.end(), value) == values.end())
        // value wasn't found within values, add it
        values.push_back(value);
}

/************************************************************************/
/* ItemRsfReader - to read .rsf files                                   */
/************************************************************************/

ItemRsfReader::ItemRsfReader(const std::string &filename) {
    std::ifstream f(filename);
    if (!f.good()) {
        Logging::warn("couldn't open file: ", filename, " checking the type of symbols will fail");
        return;
    }
    std::string item;
    // if a line starts with Item, read the symbol and type information and store them together
    while (f >> item) {
        if(item != "Item") {
            std::getline(f, item); // discard the remaining line
            continue;
        }
        std::string symbol, type;
        f >> symbol >> type;
        this->emplace(symbol, type);
    }
}

const std::string *ItemRsfReader::getValue(const std::string &key) const {
    auto i = find(key);
    if (i == end())  // key not found
        return nullptr;
    return &(i->second);
}
