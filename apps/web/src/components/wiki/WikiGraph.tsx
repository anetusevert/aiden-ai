'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import {
  apiClient,
  type WikiGraphNode,
  type WikiGraphEdge,
} from '@/lib/apiClient';
import { useNavigation } from '@/components/NavigationLoader';

const CATEGORY_COLORS: Record<string, string> = {
  law: 'rgba(255,255,255,0.92)',
  regulation: 'rgba(255,255,255,0.82)',
  concept: 'rgba(255,255,255,0.72)',
  entity: 'rgba(255,255,255,0.62)',
  research: 'rgba(255,255,255,0.52)',
  synthesis: 'rgba(255,255,255,0.9)',
  case: 'rgba(255,255,255,0.78)',
};

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  slug: string;
  title: string;
  category: string;
  jurisdiction: string | null;
  inbound_link_count: number;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  context: string;
}

export function WikiGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { navigateTo } = useNavigation();
  const [loading, setLoading] = useState(true);
  const [empty, setEmpty] = useState(false);

  const navigateRef = useRef(navigateTo);
  navigateRef.current = navigateTo;

  const initGraph = useCallback(
    (nodes: WikiGraphNode[], edges: WikiGraphEdge[]) => {
      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();

      const container = containerRef.current;
      if (!container) return;
      const width = container.clientWidth;
      const height = container.clientHeight;

      svg.attr('width', width).attr('height', height);

      const g = svg.append('g');

      // Zoom
      const zoom = d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.3, 3])
        .on('zoom', event => {
          g.attr('transform', event.transform);
        });
      svg.call(zoom as any);

      const simNodes: SimNode[] = nodes.map(n => ({ ...n }));
      const nodeMap = new Map(simNodes.map(n => [n.id, n]));
      const simLinks: SimLink[] = edges
        .filter(e => nodeMap.has(e.from) && nodeMap.has(e.to))
        .map(e => ({ source: e.from, target: e.to, context: e.context }));

      const simulation = d3
        .forceSimulation(simNodes)
        .force(
          'link',
          d3
            .forceLink<SimNode, SimLink>(simLinks)
            .id(d => d.id)
            .distance(80)
            .strength(0.5)
        )
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force(
          'collide',
          d3.forceCollide<SimNode>().radius(d => getRadius(d) + 4)
        );

      // Edges
      const link = g
        .append('g')
        .selectAll('line')
        .data(simLinks)
        .enter()
        .append('line')
        .attr('stroke', 'rgba(255,255,255,0.08)')
        .attr('stroke-width', 1)
        .style('opacity', 0);

      link
        .transition()
        .delay(nodes.length * 20 + 100)
        .duration(300)
        .style('opacity', 1);

      // Nodes
      const node = g
        .append('g')
        .selectAll('circle')
        .data(simNodes)
        .enter()
        .append('circle')
        .attr('r', d => getRadius(d))
        .attr('fill', d => CATEGORY_COLORS[d.category] || '#888')
        .attr('stroke', 'rgba(255,255,255,0.2)')
        .attr('stroke-width', 1)
        .style('opacity', 0)
        .style('cursor', 'pointer');

      node.each(function (_, i) {
        d3.select(this)
          .transition()
          .delay(i * 20)
          .duration(300)
          .style('opacity', 0.85);
      });

      // Tooltip interactions
      const tooltip = d3.select(tooltipRef.current);

      node
        .on('mouseover', (event, d) => {
          tooltip
            .style('display', 'block')
            .style('left', event.offsetX + 12 + 'px')
            .style('top', event.offsetY + 12 + 'px')
            .html(
              `<strong>${d.title}</strong><br/><span class="badge badge-muted" style="font-size:10px">${d.category}</span>`
            );
        })
        .on('mousemove', event => {
          tooltip
            .style('left', event.offsetX + 12 + 'px')
            .style('top', event.offsetY + 12 + 'px');
        })
        .on('mouseout', () => {
          tooltip.style('display', 'none');
        })
        .on('click', (_, d) => {
          navigateRef.current(`/wiki/${d.slug}`);
        });

      // Drag
      const drag = d3
        .drag<SVGCircleElement, SimNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        });
      node.call(drag);

      simulation.on('tick', () => {
        link
          .attr('x1', d => (d.source as SimNode).x!)
          .attr('y1', d => (d.source as SimNode).y!)
          .attr('x2', d => (d.target as SimNode).x!)
          .attr('y2', d => (d.target as SimNode).y!);
        node.attr('cx', d => d.x!).attr('cy', d => d.y!);
      });
    },
    []
  );

  useEffect(() => {
    apiClient
      .getWikiGraph()
      .then(data => {
        setLoading(false);
        if (data.nodes.length === 0) {
          setEmpty(true);
          return;
        }
        initGraph(data.nodes, data.edges);
      })
      .catch(() => {
        setLoading(false);
        setEmpty(true);
      });
  }, [initGraph]);

  return (
    <div ref={containerRef} className="wiki-graph-col">
      {loading && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
          }}
        >
          <span className="spinner spinner-lg" />
        </div>
      )}
      {empty && !loading && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--text-muted)',
            textAlign: 'center',
            padding: 40,
          }}
        >
          Your wiki graph will appear here as Amin builds knowledge pages.
        </div>
      )}
      <svg ref={svgRef} className="wiki-graph-svg" />
      <div
        ref={tooltipRef}
        style={{
          display: 'none',
          position: 'absolute',
          background: 'rgba(20,20,30,0.95)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '8px 12px',
          fontSize: 13,
          color: '#fff',
          pointerEvents: 'none',
          zIndex: 20,
          maxWidth: 220,
        }}
      />
    </div>
  );
}

function getRadius(node: SimNode): number {
  return Math.min(6 + node.inbound_link_count * 2, 20);
}
