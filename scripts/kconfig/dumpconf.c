/*
 * Copyright (C) 2009 Reinhard Tartler
 * Copyright (C) 2015 Stefan Hengelein <stefan.hengelein@fau.de>
 *
 * Released under the terms of the GNU GPL v2.0.
 */

#include <ctype.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

#define LKC_DIRECT_LINK
#include "lkc.h"


static bool isHex(const char *str) {
	if (str[0] != '0' || !(str[1] == 'x' || str[1] == 'X'))
		return false;
	str += 2;
	int i = *str++;
	do {
		if (!isxdigit(i))
			return false;
	} while ((i = *str++));
	return true;
}

static bool isInt(const char *str) {
	int ch = *str++;
	if (ch == '-')
		ch = *str++;
	if (!isdigit(ch) || (ch == '0' && *str != 0))
		return false;
	while ((ch = *str++))
		if (!isdigit(ch))
			return false;
	return true;
}

static void printSymbol(FILE *out, struct symbol *sym, char *choice) {
	if (sym == &symbol_mod)
		fputs("m", out);
	else if (sym == &symbol_yes)
		fputs("y", out);
	else if (sym == &symbol_no)
		fputs("n", out);
	else if (sym->flags & SYMBOL_CONST || (sym->type == S_UNKNOWN
										   && (isHex(sym->name) || isInt(sym->name))))
		fprintf(out, "CVALUE_%s", sym->name);
//	else if (sym->type == S_INT || sym->type == S_HEX || sym->type == S_STRING)
//		fprintf(out, "-%s-", sym->name);
//	else if (sym->type == S_UNKNOWN)		// mostly missing symbols
//		fprintf(out, "'%s'", sym->name);
	else if (sym->name)
		fputs(sym->name, out);
	else if (choice)
		fputs(choice, out);
	else if (sym->flags & SYMBOL_AUTO)
		// if a symbol has a "depends on m" statement, kconfig will create an internal symbol
		// with flag SYMBOL_AUTO in the dependency, with no name. Ignore it.
		fputs("CADOS_IGNORED", out);
	else
		fprintf(out, "SYM@%p", sym);
}

static int choice_count = 0;

// based on expr_print() from expr.c
static void my_expr_print(struct expr *e, void *out, int prevtoken, char *choice) {
	if (!e) {
		fputs("y", out);
		return;
	}

	if (expr_compare_type(prevtoken, e->type) > 0)
		fputs("(", out);
	switch (e->type) {
	case E_SYMBOL:
		printSymbol(out, e->left.sym, choice);
		break;
	case E_NOT:
		fputs("!", out);
		my_expr_print(e->left.expr, out, E_NOT, choice);
		break;
	case E_EQUAL:
		printSymbol(out, e->left.sym, choice);
		fputs("=", out);
		printSymbol(out, e->right.sym, choice);
		break;
	case E_UNEQUAL:
		printSymbol(out, e->left.sym, choice);
		fputs("!=", out);
		printSymbol(out, e->right.sym, choice);
		break;
	case E_OR:
		my_expr_print(e->left.expr, out, E_OR, choice);
		fputs(" || ", out);
		my_expr_print(e->right.expr, out, E_OR, choice);
		break;
	case E_AND:
		my_expr_print(e->left.expr, out, E_AND, choice);
		fputs(" && ", out);
		my_expr_print(e->right.expr, out, E_AND, choice);
		break;
	case E_LIST:
		printSymbol(out, e->right.sym, choice);
		if (e->left.expr) {
			fputs(" ^ ", out);
			my_expr_print(e->left.expr, out, E_LIST, choice);
		}
		break;
	case E_RANGE:
		fputs("[", out);
		printSymbol(out, e->left.sym, choice);
		fputs(" ", out);
		printSymbol(out, e->right.sym, choice);
		fputs("]", out);
		break;
	default:
		fprintf(out, "<unknown type %d>", e->type);
		break;
	}
	if (expr_compare_type(prevtoken, e->type) > 0)
		fputs(")", out);
}

static void my_print_symbol(FILE *out, struct menu *menu, char *choice) {
	struct symbol *sym = menu->sym;

	if (!sym_is_choice(sym)) {
		if (sym_is_choice_value(sym))
			fprintf(out, "ChoiceItem\t%s\t%s\n", sym->name, choice);

		fprintf(out, "Item\t%s\t%s\n", sym->name, sym_type_name(sym->type));
	}

	char itemname[50];
	int has_prompts = 0;
	struct property *prop;

	snprintf(itemname, sizeof itemname, "%s", sym->name ? sym->name : choice);

	if (menu->dep) {
		fprintf(out, "Depends\t%s\t\"", itemname);
		my_expr_print(menu->dep, out, E_NONE, choice);
		fprintf(out, "\"\n");
	}

	for_all_prompts(sym, prop)
		has_prompts++;

	fprintf(out, "HasPrompts\t%s\t%d\n", itemname, has_prompts);

	for_all_properties(sym, prop, P_DEFAULT) {
		fprintf(out, "Default\t%s\t\"", itemname);
		my_expr_print(prop->expr, out, E_NONE, choice);
		fprintf(out, "\"\t\"");
		my_expr_print(prop->visible.expr, out, E_NONE, choice);
		fprintf(out, "\"\n");
	}
	for_all_properties(sym, prop, P_SELECT) {
		fprintf(out, "ItemSelects\t%s\t\"", itemname);
		my_expr_print(prop->expr, out, E_NONE, choice);
		fprintf(out, "\"\t\"");
		my_expr_print(prop->visible.expr, out, E_NONE, choice);
		fprintf(out, "\"\n");
	}
	fprintf(out, "Definition\t%s\t\"%s:%d\"\n", itemname, menu->file->name, menu->lineno);

//	for_all_properties(sym, prop, P_RANGE) {
//		fprintf(out, "Range\t%s\t\"", itemname);
//		my_expr_print(prop->expr, out, E_NONE, choice);
//		fprintf(out, "\"\t\"");
//		my_expr_print(prop->visible.expr, out, E_NONE, choice);
//		fprintf(out, "\"\n");
//	}

	if (sym_is_choice_value(sym))
		fputs("#choice value\n", out);
}

static void handleChoice(FILE *out, struct menu *menu);

static void handleSymbol(FILE *out, struct menu *menu, char *choice) {
	struct menu *child;
	bool was_choice = false;
	if (menu->sym) {
		if (sym_is_choice(menu->sym)) {
			handleChoice(out, menu);
			was_choice = true;
		} else {
			my_print_symbol(out, menu, choice);
		}
	}
	if (!was_choice)
		for (child = menu->list; child; child = child->next)
			// non-choice-values have a dependency on a choice if they are defined within a
			// choice structure, thus we have to forward the choice argument
			handleSymbol(out, child, choice);
}

static void handleChoice(FILE *out, struct menu *menu) {
	char buf[12];
	struct menu *child;

	fprintf(out, "#startchoice\n");
	choice_count++;

	snprintf(buf, sizeof buf, "CHOICE_%d", choice_count);
	fprintf(out, "Choice\t%s", buf);

	// optional, i.e. all items can be deselected
	if (sym_is_optional(menu->sym))
		fprintf(out, "\toptional");
	else
		fprintf(out, "\trequired");

	if (menu->sym->type & S_TRISTATE)
		fprintf(out, "\ttristate");
	else
		fprintf(out, "\tboolean");

	fprintf(out, "\n");

	my_print_symbol(out, menu, buf);

	for (child = menu->list; child; child = child->next)
		handleSymbol(out, child, buf);

	fprintf(out, "#endchoice\t%s\n", buf);
}

static void myconfdump(FILE *out) {
	struct menu *child;
	for (child = &rootmenu; child; child = child->next)
		handleSymbol(out, child, NULL);
}

int main(int ac, char **av) {
	struct stat tmpstat;
	char *arch = getenv("ARCH");

	setlocale(LC_ALL, "");
	bindtextdomain(PACKAGE, LOCALEDIR);
	textdomain(PACKAGE);

	if (stat(av[1], &tmpstat) != 0) {
		fprintf(stderr, "could not open %s\n", av[1]);
		exit(EXIT_FAILURE);
	}

	if (!arch) {
		fputs("setting arch to default: x86\n", stderr);
		arch = "x86";
		setenv("ARCH", arch, 1);
	}
	fprintf(stderr, "using arch %s\n", arch);
	setenv("KERNELVERSION", "2.6.30-vamos", 1);
	conf_parse(av[1]);
	myconfdump(stdout);
	return EXIT_SUCCESS;
}
