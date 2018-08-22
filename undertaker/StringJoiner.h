/*
 *   undertaker - analyze preprocessor blocks in code
 *
 * Copyright (C) 2009-2011 Reinhard Tartler <tartler@informatik.uni-erlangen.de>
 * Copyright (C) 2009-2011 Julio Sincero <Julio.Sincero@informatik.uni-erlangen.de>
 * Copyright (C) 2010-2011 Christian Dietrich <christian.dietrich@informatik.uni-erlangen.de>
 * Copyright (C) 2014 Stefan Hengelein <stefan.hengelein@fau.de>
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
#ifndef string_joiner_h__
#define string_joiner_h__

#include <deque>
#include <set>
#include <string>
#include <sstream>


/**
 * \brief Helper subclass of std::deque<std::string> for convenient
 *  concatenating strings with a separator.
 *
 * The behaviour is similar to the python list().join(",") construct.
 */
struct StringJoiner : public std::deque<std::string> {
    /**
     * \brief join all strings in the container,
     *
     * Join all the collected strings to one string. The separator is
     * inserted between each element.
     */
    std::string join(const std::string &j) const {
        if (size() == 0)
            return "";

        std::stringstream ss;
        ss << front();

        for (auto it = begin() + 1, e = end(); it != e; ++it)
            ss << j << *it;

        return ss.str();
    }
    /**
     * \brief append strings to list.
     *
     * Appends the given value to the list of values. The empty string "" will be ignored.
     */
    void push_back(const value_type &x) {
        if (x == "")
            return;
        std::deque<value_type>::push_back(x);
    }
    /**
     * \brief append strings to list.
     *
     * Appends the given value to the list of values. The empty string "" will be ignored.
     */
    void emplace_back(const value_type &x) {
        if (x == "")
            return;
        std::deque<value_type>::emplace_back(x);
    }
    /**
     * \brief prepend strings to list.
     *
     * Prepends the given value to the list of values. The empty string "" will be ignored.
     */
    void push_front(const value_type &x) {
        if (x == "")
            return;
        std::deque<value_type>::push_front(x);
    }
    /**
     * \brief prepend strings to list.
     *
     * Prepends the given value to the list of values. The empty string "" will be ignored.
     */
    void emplace_front(const value_type &x) {
        if (x == "")
            return;
        std::deque<value_type>::emplace_front(x);
    }
};

struct UniqueStringJoiner : public StringJoiner {
    void push_back(const value_type &x) {
        if (uniqueFlag) {
            /* Simulate a set when StringJoiner is unique,
             * return if 'x' was already in the unique_set */
            if (!(_unique_set.insert(x)).second)
                return;
        }
        StringJoiner::push_back(x);
    }

    void emplace_back(const value_type &x) {
        if (uniqueFlag) {
            /* Simulate a set when StringJoiner is unique,
             * return if 'x' was already in the unique_set */
            if (!(_unique_set.insert(x)).second)
                return;
        }
        StringJoiner::emplace_back(x);
    }

    void push_front(const value_type &x) {
        if (uniqueFlag) {
            /* Simulate a set when StringJoiner is unique,
             * return if 'x' was already in the unique_set */
            if (!(_unique_set.insert(x)).second)
                return;
        }
        StringJoiner::push_front(x);
    }

    void emplace_front(const value_type &x) {
        if (uniqueFlag) {
            /* Simulate a set when StringJoiner is unique,
             * return if 'x' was already in the unique_set */
            if (!(_unique_set.insert(x)).second)
                return;
        }
        StringJoiner::emplace_front(x);
    }

    void disableUniqueness() { uniqueFlag = false; }

private:
    bool uniqueFlag = true;
    std::set<std::string> _unique_set;
};
#endif
