// Refine an existing order without moving functions across ineligible functions.
// Addresses below describe a packed layout using BOLT's estimated function sizes;
// they are a locality model, not final emitted addresses (alignment may differ).
static void refineSmallFunctionLayout(BinaryContext &BC) {
  const bool HasHotTextMovers =
      opts::HotText &&
      llvm::any_of(llvm::make_second_range(BC.getBinaryFunctions()),
                   [](const BinaryFunction &BF) {
                     return opts::isHotTextMover(BF);
                   });
  if (!BC.HasRelocations || !opts::FunctionOrderFile.empty() ||
      opts::HotFunctionsAtEnd || HasHotTextMovers ||
      opts::ReorderFunctions == ReorderFunctions::RT_USER ||
      opts::ReorderFunctions == ReorderFunctions::RT_RANDOM) {
    BC.outs() << "BOLT-INFO: small-function-layout: skipped (unsupported order)\n";
    return;
  }

  // Build a fresh graph: CDSort may have adjusted the original graph's weights.
  // Do not recover stale profiles or substitute block counts for call counts.
  BinaryFunctionCallGraph Graph = buildCallGraph(
      BC,
      [&BC](const BinaryFunction &BF) {
        return !BC.shouldEmit(BF) || !BF.hasValidProfile() || BF.isIgnored() ||
               BF.getState() != BinaryFunction::State::CFG;
      },
      /*CgFromPerfData=*/false, /*IncludeSplitCalls=*/true,
      /*UseFunctionHotSize=*/false, /*UseSplitHotSize=*/false,
      /*UseEdgeCounts=*/true, /*IgnoreRecursiveCalls=*/true);
  // This also finalizes the weighted average call-site offsets.
  Graph.normalizeArcWeights();

  BinaryFunctionListType Order;
  for (auto &It : BC.getBinaryFunctions())
    if (BC.shouldEmit(It.second))
      Order.push_back(&It.second);
  llvm::stable_sort(Order, compareBinaryFunctionByIndex);

  std::vector<uint64_t> Address(Graph.numNodes());
  uint64_t Offset = 0;
  for (BinaryFunction *BF : Order) {
    NodeId Id = Graph.maybeGetNodeId(BF);
    if (Id != CallGraph::InvalidId)
      Address[Id] = Offset;
    Offset += std::max<uint64_t>(BF->estimateSize(), 1);
  }

  struct Edge {
    NodeId Src, Dst;
    double Weight, CallOffset;
  };
  std::vector<Edge> Edges;
  std::vector<std::vector<size_t>> Incident(Graph.numNodes());
  for (NodeId Src = 0; Src < Graph.numNodes(); ++Src) {
    for (NodeId Dst : Graph.successors(Src)) {
      const Arc &A = *Graph.findArc(Src, Dst);
      if (Src == Dst || !Graph.nodeIdToFunc(Src)->hasValidProfile() ||
          !Graph.nodeIdToFunc(Dst)->hasValidProfile() ||
          !std::isfinite(A.weight()) || A.weight() <= 0 ||
          !std::isfinite(A.avgCallOffset()) || A.avgCallOffset() < 0)
        continue;
      Incident[Src].push_back(Edges.size());
      Incident[Dst].push_back(Edges.size());
      Edges.push_back({Src, Dst, A.weight(), A.avgCallOffset()});
    }
  }

  auto Cost = [&](const Edge &E) -> long double {
    return static_cast<long double>(E.Weight) *
           std::abs(static_cast<long double>(Address[E.Src]) + E.CallOffset -
                    static_cast<long double>(Address[E.Dst]));
  };
  auto TotalCost = [&]() {
    long double Total = 0;
    for (const Edge &E : Edges)
      Total += Cost(E);
    return Total;
  };
  auto Eligible = [&](BinaryFunction *BF) {
    NodeId Id = Graph.maybeGetNodeId(BF);
    return Id != CallGraph::InvalidId && !Incident[Id].empty() &&
           BF->hasValidIndex() && BF->hasValidProfile() && BF->isSimple() &&
           !BF->isIgnored() && !BF->isPLTFunction() && !BF->isSplit() &&
           BF->getState() == BinaryFunction::State::CFG &&
           BF->getKnownExecutionCount() >= 100 && BF->estimateSize() > 0 &&
           BF->estimateSize() <= 128 && !opts::padFunctionBefore(*BF) &&
           !opts::padFunctionAfter(*BF);
  };

  if (Edges.empty()) {
    BC.outs() << "BOLT-INFO: small-function-layout: skipped (no valid call edges)\n";
    return;
  }

  const long double Before = TotalCost();
  uint64_t Swaps = 0;
  // A fixed bound keeps the refinement inexpensive and deterministic.
  for (unsigned Round = 0; Round < 64; ++Round) {
    bool Changed = false;
    for (size_t I = 1; I < Order.size(); ++I) {
      BinaryFunction *Left = Order[I - 1], *Right = Order[I];
      if (!Eligible(Left) || !Eligible(Right))
        continue;
      NodeId A = Graph.maybeGetNodeId(Left);
      NodeId B = Graph.maybeGetNodeId(Right);
      // Only edges incident to A or B can change. Include external edges and
      // count shared edges once; inspecting only A<->B would miss regressions.
      auto AffectedCost = [&]() {
        long double Total = 0;
        for (size_t E : Incident[A])
          Total += Cost(Edges[E]);
        for (size_t E : Incident[B])
          if (Edges[E].Src != A && Edges[E].Dst != A)
            Total += Cost(Edges[E]);
        return Total;
      };
      const long double OldCost = AffectedCost();
      const uint64_t OldA = Address[A], OldB = Address[B];
      Address[B] = OldA;
      Address[A] = OldA + Right->estimateSize();
      const long double NewCost = AffectedCost();
      if (NewCost + 1e-12L * std::max(1.0L, OldCost) < OldCost) {
        Left->swapIndex(*Right);
        std::swap(Order[I - 1], Order[I]);
        ++Swaps;
        Changed = true;
      } else {
        Address[A] = OldA;
        Address[B] = OldB;
      }
    }
    if (!Changed)
      break;
  }
  BC.outs() << "BOLT-INFO: small-function-layout: swaps=" << Swaps
            << format(" weighted-distance-before=%.0f after=%.0f\n",
                      static_cast<double>(Before),
                      static_cast<double>(TotalCost()));
}

