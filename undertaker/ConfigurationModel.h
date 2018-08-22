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

// -*- mode: c++ -*-
#ifndef configuration_model_h__
#define configuration_model_h__

#include <string>
#include <set>
#include <deque>
#include <boost/regex.hpp>

using StringList = std::deque<std::string>;
struct StringJoiner;


class ConfigurationModel {
    virtual void doIntersectPreprocess(std::set<std::string> &start_items, StringJoiner &sj,
                                       std::set<std::string> *exclude_set) const = 0;

    virtual void addMetaValue(const std::string &key, const std::string &feature) const = 0;

public:
    //! destructor
    virtual ~ConfigurationModel(){};

    //! returns the version identifier for the current model
    virtual const std::string getModelVersionIdentifier() const = 0;

    //@{
    //! checks the type of a given symbol.
    //! @return false if not found
    virtual bool isBoolean(const std::string &) const = 0;
    virtual bool isTristate(const std::string &) const = 0;
    //@}

    //! returns the type of the given symbol
    /*!
     * Normalizes the given item so that passing with and without
     * CONFIG_ prefix works.
     */
    virtual std::string getType(const std::string &feature_name) const = 0;

    virtual bool containsSymbol(const std::string &symbol) const = 0;

    virtual const StringList *getMetaValue(const std::string &key) const = 0;

/************************************************************************/
/* non virtual methods                                                  */
/************************************************************************/

    std::set<std::string> doIntersect(const std::string exp,
                                      const std::function<bool(std::string)> &c,
                                      std::set<std::string> &missing, std::string &intersected,
                                      std::set<std::string> *exclude_set = nullptr) const;

    //! add feature to whitelist ('ALWAYS_ON')
    void addFeatureToWhitelist(const std::string &feature);

    //! gets the current feature whitelist ('ALWAYS_ON')
    //! The referenced object must not be freed, the model class manages it.
    const StringList *getWhitelist() const;

    //! add feature to blacklist ('ALWAYS_OFF')
    void addFeatureToBlacklist(const std::string &feature);

    //!< gets the current feature blacklist ('ALWAYS_OFF')
    //! The referenced object must not be freed, the model class manages it.
    const StringList *getBlacklist() const;

    //! checks if we can assume that the configuration space is complete
    bool isComplete() const;
    //! checks if a given item should be in the model space
    bool inConfigurationSpace(const std::string &symbol) const;
    std::string getName() const { return _name; }

    static std::string getMissingItemsConstraints(const std::set<std::string> &missing);

protected:
    ConfigurationModel() = default;

    std::string _name;
    boost::regex _inConfigurationSpace_regexp;
};
#endif
