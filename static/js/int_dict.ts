import * as _ from 'underscore';

/*
    If we know our keys are ints, the
    map-based implementation is about
    20% faster than if we have to normalize
    keys as strings.  Of course, this
    requires us to be a bit careful in the
    calling code.  We validate ints, which
    is cheap, but we don't handle them; we
    just report errors.

    This has a subset of methods from our old
    Dict class, so it's not quite a drop-in
    replacement.  For things like setdefault,
    it's easier to just use a two-liner in the
    calling code.  If your Dict uses from_array,
    convert it to a Set, not an IntDict.
*/

export class IntDict<V> {
    private _map = new Map();

    get(key: number): V | undefined {
        key = this._convert(key);
        return this._map.get(key);
    }

    set(key: number, value: V): V {
        key = this._convert(key);
        this._map.set(key, value);
        return value;
    }

    has(key: number): boolean {
        key = this._convert(key);
        return this._map.has(key);
    }

    del(key: number): void {
        key = this._convert(key);
        this._map.delete(key);
    }

    keys(): number[] {
        return Array.from(this._map.keys());
    }

    values(): V[] {
        return Array.from(this._map.values());
    }

    num_items(): number {
        return this._map.size;
    }

    is_empty(): boolean {
        return this._map.size === 0;
    }

    each(f: (v: V, k?: number) => void): void {
        this._map.forEach(f);
    }

    clear(): void {
        this._map.clear();
    }

    private _convert(key: number): number {
        // These checks are cheap! (at least on node.js)
        if (key === undefined) {
            blueslip.error("Tried to call a IntDict method with an undefined key.");
            return key;
        }

        if (typeof key !== 'number') {
            blueslip.error("Tried to call a IntDict method with a non-integer.");
            // @ts-ignore
            return parseInt(key, 10);
        }

        return key;
    }
}
