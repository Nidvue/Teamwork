import { Plugin } from "@opencode/plugin/tui";
import { createSignal, For } from "solid-js";
import { defineStatusPlugin } from "./index";

export default Plugin.define(
  defineStatusPlugin(() => {
    const [lines, setLines] = createSignal<string[]>([]);
    return {
      element: () => (
        <box flexDirection="column">
          <For each={lines()}>{(line) => <text>{line}</text>}</For>
        </box>
      ),
      update: (next) => setLines(next),
    };
  }),
);
